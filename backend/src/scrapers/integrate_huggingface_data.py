#!/usr/bin/env python3
"""
Integration script for HuggingFace Open LLM Leaderboard data
Processes scraped data and adds it to the leaderboard database
"""

import sys
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.append(str(backend_dir))

from src.db.database import SessionLocal
from src.models.models import Model, Score, ScrapingRun

def load_huggingface_data(file_path: str):
    """Load HuggingFace data from JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def integrate_huggingface_data(data_file: str):
    """Integrate HuggingFace Open LLM Leaderboard data into database"""
    print(f"🤗 Starting HuggingFace Open LLM Leaderboard data integration...")
    print(f"Data file: {data_file}")
    
    # Load data
    try:
        huggingface_data = load_huggingface_data(data_file)
        print(f"✅ Loaded {len(huggingface_data)} model entries from file")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return False
    
    db = SessionLocal()
    
    try:
        # Create scraping run record
        scraping_run = ScrapingRun(
            source="HuggingFace Open LLM Leaderboard",
            timestamp=datetime.now(),
            status="completed",
            models_found=len(huggingface_data),
            models_added=0,
            error_message=None
        )
        db.add(scraping_run)
        db.flush()  # Get the ID
        
        models_added = 0
        scores_added = 0
        
        # Map HuggingFace benchmarks to our categories
        benchmark_categories = {
            'IFEval': 'reasoning',
            'BBH': 'reasoning', 
            'MATH': 'reasoning',
            'GPQA': 'knowledge',
            'MUSR': 'reasoning',
            'MMLU-PRO': 'knowledge',
            'Average': 'overall'
        }
        
        print(f"\n📊 Processing model entries...")
        
        for model_data in huggingface_data:
            try:
                model_name = model_data['model']
                
                # Check if model already exists
                existing_model = db.query(Model).filter(Model.name == model_name).first()
                
                if existing_model:
                    model = existing_model
                    print(f"   📝 Found existing model: {model_name}")
                else:
                    # Create new model
                    model = Model(
                        name=model_name,
                        provider="HuggingFace",
                        model_type=model_data.get('model_type', 'unknown'),
                        size_category="large" if "72B" in model_name or "78B" in model_name else "medium",
                        description=f"Model from HuggingFace Open LLM Leaderboard (Rank #{model_data.get('rank', 'N/A')})",
                        created_at=datetime.now()
                    )
                    db.add(model)
                    db.flush()  # Get the model ID
                    models_added += 1
                    print(f"   ✅ Added new model: {model_name}")
                
                # Add scores for each benchmark
                for benchmark_name, score_value in model_data['scores'].items():
                    if score_value is not None:
                        category = benchmark_categories.get(benchmark_name, 'other')
                        
                        # Check if score already exists for this model/benchmark
                        existing_score = db.query(Score).filter(
                            Score.model_id == model.id,
                            Score.benchmark == benchmark_name,
                            Score.source == "HuggingFace Open LLM Leaderboard"
                        ).first()
                        
                        if existing_score:
                            # Update existing score
                            existing_score.score = score_value
                            existing_score.timestamp = datetime.now()
                            existing_score.scraping_run_id = scraping_run.id
                        else:
                            # Create new score
                            score = Score(
                                model_id=model.id,
                                benchmark=benchmark_name,
                                score=score_value,
                                category=category,
                                source="HuggingFace Open LLM Leaderboard",
                                timestamp=datetime.now(),
                                scraping_run_id=scraping_run.id,
                                metadata={
                                    'rank': model_data.get('rank'),
                                    'model_type': model_data.get('model_type'),
                                    'co2_cost': model_data.get('metadata', {}).get('co2_cost')
                                }
                            )
                            db.add(score)
                            scores_added += 1
                
            except Exception as e:
                print(f"   ❌ Error processing model {model_data.get('model', 'unknown')}: {e}")
                continue
        
        # Update scraping run
        scraping_run.models_added = models_added
        
        # Commit all changes
        db.commit()
        
        print(f"\n🎯 INTEGRATION COMPLETED!")
        print(f"✅ Models added/updated: {models_added}")
        print(f"✅ Scores added: {scores_added}")
        print(f"✅ Source: HuggingFace Open LLM Leaderboard")
        print(f"✅ Benchmarks: IFEval, BBH, MATH, GPQA, MUSR, MMLU-PRO")
        print(f"✅ Categories: reasoning, knowledge, overall")
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        db.rollback()
        return False
    
    finally:
        db.close()

def main():
    """Main integration function"""
    # Find the most recent HuggingFace data file
    sources_dir = Path(__file__).parent / "sources"
    huggingface_files = list(sources_dir.glob("huggingface_open_llm_data_*.json"))
    
    if not huggingface_files:
        print("❌ No HuggingFace data files found")
        print("💡 Run the HuggingFace scraper first:")
        print("   python sources/huggingface_open_llm_scraper.py")
        return
    
    # Use the most recent file
    latest_file = max(huggingface_files, key=lambda f: f.stat().st_mtime)
    print(f"📁 Using latest data file: {latest_file.name}")
    
    # Integrate the data
    success = integrate_huggingface_data(str(latest_file))
    
    if success:
        print("\n✅ HuggingFace Open LLM Leaderboard integration completed successfully!")
        print("🎯 Ready to proceed with Task 4.1 completion")
    else:
        print("\n❌ Integration failed")

if __name__ == "__main__":
    main() 