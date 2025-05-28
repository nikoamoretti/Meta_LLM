#!/usr/bin/env python3
"""
Integration script to add HuggingFace Open LLM Leaderboard data to our leaderboard system
Based on the successful strawberry_bench integration pattern
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pathlib import Path

from src.db.models import Base, Leaderboard, RawScore

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "sqlite:///./meta_llm.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create database tables if they don't exist"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

def add_huggingface_leaderboard(db):
    """Add HuggingFace Open LLM Leaderboard as a leaderboard in our system"""
    
    # Check if already exists
    existing = db.query(Leaderboard).filter(Leaderboard.name == "HuggingFace Open LLM").first()
    if existing:
        logger.info("HuggingFace Open LLM leaderboard already exists")
        return existing.id
    
    # Create new leaderboard entry
    leaderboard = Leaderboard(
        name="HuggingFace Open LLM",
        category="comprehensive"
    )
    
    db.add(leaderboard)
    db.commit()
    db.refresh(leaderboard)
    
    logger.info(f"Created HuggingFace Open LLM leaderboard with ID: {leaderboard.id}")
    return leaderboard.id

def import_huggingface_data(db, leaderboard_id):
    """Import scraped HuggingFace Open LLM data into database"""
    
    # Find the data file
    sources_dir = Path("src/scrapers/sources")
    huggingface_files = list(sources_dir.glob("huggingface_open_llm_data_*.json"))
    
    if not huggingface_files:
        logger.error("No HuggingFace data files found. Run the scraper first.")
        return 0
    
    # Use the most recent file
    latest_file = max(huggingface_files, key=lambda f: f.stat().st_mtime)
    logger.info(f"Using data file: {latest_file}")
    
    # Load the scraped data
    try:
        with open(latest_file, 'r') as f:
            huggingface_data = json.load(f)
        
        if not huggingface_data:
            logger.error("No HuggingFace data found in file")
            return 0
        
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return 0
    
    # Clear existing HuggingFace data
    db.query(RawScore).filter(RawScore.leaderboard_id == leaderboard_id).delete()
    db.commit()
    logger.info("Cleared existing HuggingFace data")
    
    imported_count = 0
    
    for model_data in huggingface_data:
        model_name = model_data['model']
        scores = model_data['scores']
        
        # Map each benchmark score as a separate entry
        benchmark_mappings = {
            'Average': {'category': 'Overall Performance', 'higher_is_better': True},
            'IFEval': {'category': 'Instruction Following', 'higher_is_better': True},
            'BBH': {'category': 'Reasoning', 'higher_is_better': True},
            'MATH': {'category': 'Mathematics', 'higher_is_better': True},
            'GPQA': {'category': 'Knowledge', 'higher_is_better': True},
            'MUSR': {'category': 'Reasoning', 'higher_is_better': True},
            'MMLU-PRO': {'category': 'Knowledge', 'higher_is_better': True}
        }
        
        for benchmark_name, score_value in scores.items():
            if score_value is not None and benchmark_name in benchmark_mappings:
                benchmark_info = benchmark_mappings[benchmark_name]
                
                raw_score = RawScore(
                    model_name=model_name,
                    leaderboard_id=leaderboard_id,
                    benchmark=benchmark_info['category'],
                    metric=benchmark_name,
                    value=float(score_value),
                    higher_is_better=benchmark_info['higher_is_better'],
                    scraped_at=datetime.now()
                )
                db.add(raw_score)
                imported_count += 1
    
    db.commit()
    logger.info(f"Imported {imported_count} score entries for {len(huggingface_data)} models")
    return imported_count

def update_api_models():
    """Update the API models to include comprehensive category"""
    
    models_file = 'src/app/api/models.py'
    
    try:
        with open(models_file, 'r') as f:
            content = f.read()
        
        # Check if comprehensive field already exists
        if 'comprehensive:' in content:
            logger.info("Comprehensive field already exists in API models")
            return
        
        # Add comprehensive field to ModelScore class
        lines = content.split('\n')
        updated_lines = []
        
        for line in lines:
            updated_lines.append(line)
            
            # Add comprehensive field after reasoning
            if 'reasoning: Optional[float] = None' in line:
                updated_lines.append('    comprehensive: Optional[float] = None')
        
        # Write back the updated content
        with open(models_file, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        logger.info("Added comprehensive field to API models")
        
    except Exception as e:
        logger.error(f"Failed to update API models: {e}")

def update_leaderboards_api():
    """Update the leaderboards API to handle comprehensive category"""
    
    api_file = 'src/app/api/leaderboards.py'
    
    try:
        with open(api_file, 'r') as f:
            content = f.read()
        
        # Check if comprehensive is already handled
        if 'comprehensive=' in content:
            logger.info("Comprehensive category already handled in API")
            return
        
        # Add comprehensive category handling
        lines = content.split('\n')
        updated_lines = []
        
        for i, line in enumerate(lines):
            updated_lines.append(line)
            
            # Add comprehensive after reasoning in get_models function
            if 'reasoning=get_category_score(db, model_name, \'reasoning\'),' in line:
                updated_lines.append('            comprehensive=get_category_score(db, model_name, \'comprehensive\'),')
            
            # Add comprehensive in get_model_detail function too
            if 'reasoning=get_category_score(db, name, \'reasoning\'),' in line:
                updated_lines.append('        comprehensive=get_category_score(db, name, \'comprehensive\'),')
        
        # Write back the updated content
        with open(api_file, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        logger.info("Updated leaderboards API to handle comprehensive category")
        
    except Exception as e:
        logger.error(f"Failed to update leaderboards API: {e}")

def main():
    """Main integration process"""
    print("🤗 Integrating HuggingFace Open LLM Leaderboard into Meta LLM")
    print("=" * 70)
    
    # Create database tables
    create_tables()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Step 1: Add HuggingFace Open LLM as a leaderboard
        logger.info("Step 1: Adding HuggingFace Open LLM leaderboard...")
        leaderboard_id = add_huggingface_leaderboard(db)
        
        # Step 2: Import the scraped data
        logger.info("Step 2: Importing HuggingFace Open LLM data...")
        imported_count = import_huggingface_data(db, leaderboard_id)
        
        if imported_count > 0:
            print(f"✅ Successfully imported {imported_count} score entries")
            
            # Step 3: Update API models
            logger.info("Step 3: Updating API models...")
            update_api_models()
            
            # Step 4: Update API endpoints
            logger.info("Step 4: Updating API endpoints...")
            update_leaderboards_api()
            
            print("✅ Integration complete!")
            print(f"🎯 HuggingFace Open LLM Leaderboard is now available")
            print(f"📊 Data includes: Average, IFEval, BBH, MATH, GPQA, MUSR, MMLU-PRO")
            print(f"🔧 API updated to include 'comprehensive' category")
            print(f"🏆 {len(set(score['model_name'] for score in db.query(RawScore).filter(RawScore.leaderboard_id == leaderboard_id).all()))} unique models added")
            
            # Show top 5 models by average score
            print(f"\n🏅 Top 5 Models by Average Score:")
            top_models = db.query(RawScore).filter(
                RawScore.leaderboard_id == leaderboard_id,
                RawScore.metric == 'Average'
            ).order_by(RawScore.value.desc()).limit(5).all()
            
            for i, model in enumerate(top_models, 1):
                print(f"  {i}. {model.model_name}: {model.value}%")
            
        else:
            print("❌ No data was imported. Check the scraper output.")
    
    except Exception as e:
        logger.error(f"Integration failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    main() 