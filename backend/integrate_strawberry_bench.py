#!/usr/bin/env python3
"""
Integration script to add Strawberry Bench data to our leaderboard system
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from src.db.models import Base, Leaderboard, RawScore
from src.scrapers.strawberry_bench_scraper import StrawberryBenchScraper

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

def add_strawberry_bench_leaderboard(db):
    """Add Strawberry Bench as a leaderboard in our system"""
    
    # Check if already exists
    existing = db.query(Leaderboard).filter(Leaderboard.name == "Strawberry Bench").first()
    if existing:
        logger.info("Strawberry Bench leaderboard already exists")
        return existing.id
    
    # Create new leaderboard entry with only the fields that exist
    leaderboard = Leaderboard(
        name="Strawberry Bench",
        category="reasoning"
    )
    
    db.add(leaderboard)
    db.commit()
    db.refresh(leaderboard)
    
    logger.info(f"Created Strawberry Bench leaderboard with ID: {leaderboard.id}")
    return leaderboard.id

def import_strawberry_data(db, leaderboard_id):
    """Import scraped Strawberry Bench data into database"""
    
    # Load the scraped data
    try:
        with open('strawberry_bench_data.json', 'r') as f:
            data = json.load(f)
        
        strawberry_models = data.get('strawberry_bench', [])
        if not strawberry_models:
            logger.error("No Strawberry Bench data found in file")
            return 0
        
    except FileNotFoundError:
        logger.error("strawberry_bench_data.json not found. Run the scraper first.")
        return 0
    
    # Clear existing Strawberry Bench data
    db.query(RawScore).filter(RawScore.leaderboard_id == leaderboard_id).delete()
    db.commit()
    logger.info("Cleared existing Strawberry Bench data")
    
    imported_count = 0
    
    for model_data in strawberry_models:
        model_name = model_data['model']
        metrics = model_data['metrics']
        
        # Import each metric as a separate score entry
        score_entries = [
            {
                'metric': 'pass_rate',
                'value': metrics.get('pass_rate', 0),
                'higher_is_better': True,
                'benchmark': 'Reasoning Tasks'
            },
            {
                'metric': 'tokens',
                'value': metrics.get('tokens', 0),
                'higher_is_better': False,  # Lower token usage is better (efficiency)
                'benchmark': 'Token Efficiency'
            },
            {
                'metric': 'cost',
                'value': metrics.get('cost', 0),
                'higher_is_better': False,  # Lower cost is better
                'benchmark': 'Cost Efficiency'
            },
            {
                'metric': 'response_time_seconds',
                'value': metrics.get('response_time_seconds', 0),
                'higher_is_better': False,  # Lower response time is better
                'benchmark': 'Speed'
            }
        ]
        
        for score_entry in score_entries:
            if score_entry['value'] is not None:  # Only add if we have the data
                raw_score = RawScore(
                    model_name=model_name,
                    leaderboard_id=leaderboard_id,
                    benchmark=score_entry['benchmark'],
                    metric=score_entry['metric'],
                    value=float(score_entry['value']),
                    higher_is_better=score_entry['higher_is_better'],
                    scraped_at=datetime.now()
                )
                db.add(raw_score)
                imported_count += 1
    
    db.commit()
    logger.info(f"Imported {imported_count} score entries for {len(strawberry_models)} models")
    return imported_count

def update_api_models():
    """Update the API models to include reasoning category"""
    
    # Read the current models file
    models_file = 'src/app/api/models.py'
    
    try:
        with open(models_file, 'r') as f:
            content = f.read()
        
        # Check if reasoning field already exists
        if 'reasoning:' in content:
            logger.info("Reasoning field already exists in API models")
            return
        
        # Add reasoning field to ModelScore class
        # Look for the line with other category fields and add reasoning
        lines = content.split('\n')
        updated_lines = []
        
        for line in lines:
            updated_lines.append(line)
            
            # Add reasoning field after multilingual
            if 'multilingual: Optional[float] = None' in line:
                updated_lines.append('    reasoning: Optional[float] = None')
        
        # Write back the updated content
        with open(models_file, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        logger.info("Added reasoning field to API models")
        
    except Exception as e:
        logger.error(f"Failed to update API models: {e}")

def update_leaderboards_api():
    """Update the leaderboards API to handle reasoning category"""
    
    api_file = 'src/app/api/leaderboards.py'
    
    try:
        with open(api_file, 'r') as f:
            content = f.read()
        
        # Check if reasoning is already handled
        if 'reasoning=' in content:
            logger.info("Reasoning category already handled in API")
            return
        
        # Add reasoning category handling
        lines = content.split('\n')
        updated_lines = []
        
        for i, line in enumerate(lines):
            updated_lines.append(line)
            
            # Add reasoning after multilingual in get_models function
            if 'multilingual=get_category_score(db, model_name, \'multilingual\'),' in line:
                updated_lines.append('            reasoning=get_category_score(db, model_name, \'reasoning\'),')
            
            # Add reasoning in get_model_detail function too
            if 'multilingual=get_category_score(db, name, \'multilingual\'),' in line:
                updated_lines.append('        reasoning=get_category_score(db, name, \'reasoning\'),')
        
        # Write back the updated content
        with open(api_file, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        logger.info("Updated leaderboards API to handle reasoning category")
        
    except Exception as e:
        logger.error(f"Failed to update leaderboards API: {e}")

def main():
    """Main integration process"""
    print("🍓 Integrating Strawberry Bench into Meta LLM Leaderboard")
    print("=" * 70)
    
    # Create database tables
    create_tables()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Step 1: Add Strawberry Bench as a leaderboard
        logger.info("Step 1: Adding Strawberry Bench leaderboard...")
        leaderboard_id = add_strawberry_bench_leaderboard(db)
        
        # Step 2: Import the scraped data
        logger.info("Step 2: Importing Strawberry Bench data...")
        imported_count = import_strawberry_data(db, leaderboard_id)
        
        if imported_count > 0:
            print(f"✅ Successfully imported {imported_count} score entries")
            
            # Step 3: Update API models
            logger.info("Step 3: Updating API models...")
            update_api_models()
            
            # Step 4: Update API endpoints
            logger.info("Step 4: Updating API endpoints...")
            update_leaderboards_api()
            
            print("✅ Integration complete!")
            print(f"🎯 Strawberry Bench reasoning benchmark is now available")
            print(f"📊 Data includes: Pass Rate, Token Efficiency, Cost Efficiency, Speed")
            print(f"🔧 API updated to include 'reasoning' category")
            
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