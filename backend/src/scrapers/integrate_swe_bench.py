#!/usr/bin/env python3
"""
SWE-Bench Verified Integration Script

Integrates SWE-Bench Verified software engineering evaluation data into the Meta LLM database.
Adds comprehensive coding capability assessment for developer adoption.

SWE-Bench Verified features:
- 500 human-verified solvable GitHub software engineering issues  
- Real-world repository issues from active open-source projects
- Stanford research with industry-standard credibility
- Percentage resolved metric for clear performance comparison
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import our database models
from src.db.models import Base, RawScore, Leaderboard
from swe_bench_scraper import SWEBenchScraper

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


class SWEBenchIntegrator:
    def __init__(self):
        self.leaderboard_name = "SWE-Bench Verified"
        self.leaderboard_category = "software_engineering"
        self.models_data = []
        
    def load_swe_bench_data(self):
        """Load SWE-Bench data via scraper"""
        try:
            scraper = SWEBenchScraper()
            self.models_data = scraper.scrape_leaderboard_data()
            benchmark_info = scraper.get_benchmark_info()
            
            print(f"📊 Loaded SWE-Bench data:")
            print(f"  Total models: {len(self.models_data)}")
            print(f"  Source: {benchmark_info['name']}")
            print(f"  Tasks: {benchmark_info['total_tasks']} verified issues")
            print(f"  Metric: {benchmark_info['evaluation_metric']}")
            
            if not self.models_data:
                raise ValueError("No models data found from scraper")
                
            return True
            
        except Exception as e:
            logger.error(f"Error loading SWE-Bench data: {e}")
            return False
    
    def create_or_get_leaderboard(self, db):
        """Create or get the SWE-Bench leaderboard entry"""
        # Check if leaderboard already exists
        existing_leaderboard = db.query(Leaderboard).filter_by(
            name=self.leaderboard_name
        ).first()
        
        if existing_leaderboard:
            print(f"📋 Found existing SWE-Bench leaderboard (ID: {existing_leaderboard.id})")
            return existing_leaderboard.id
        
        # Create new leaderboard
        new_leaderboard = Leaderboard(
            name=self.leaderboard_name,
            category=self.leaderboard_category
        )
        
        db.add(new_leaderboard)
        db.commit()
        db.refresh(new_leaderboard)
        
        print(f"✅ Created new SWE-Bench leaderboard (ID: {new_leaderboard.id})")
        return new_leaderboard.id
    
    def clean_model_name(self, name: str) -> str:
        """Clean model name removing prefixes and emojis"""
        # Remove common prefixes and emojis
        prefixes_to_remove = ['✅', '🆕', '🔥', '⭐', '🎯', '💎', '🚀']
        
        cleaned = name
        for prefix in prefixes_to_remove:
            cleaned = cleaned.replace(prefix, '')
        
        return cleaned.strip()
    
    def integrate_swe_bench_scores(self, db, leaderboard_id):
        """Integrate all SWE-Bench model scores into the database"""
        print(f"\n🔄 Integrating SWE-Bench scores...")
        
        # Clear existing scores for this leaderboard (in case of re-run)
        deleted_count = db.query(RawScore).filter_by(
            leaderboard_id=leaderboard_id
        ).delete()
        
        if deleted_count > 0:
            print(f"🗑️ Cleared {deleted_count} existing SWE-Bench scores")
            db.commit()
        
        # Integration counters
        successful_integrations = 0
        total_score_entries = 0
        
        for model_data in self.models_data:
            try:
                model_name = self.clean_model_name(model_data.get('model_name', ''))
                resolved_percent = model_data.get('resolved_percent')
                
                if not model_name or resolved_percent is None:
                    logger.warning(f"Skipping model with missing data: {model_data}")
                    continue
                
                # Create score entry for percentage resolved
                score_entry = RawScore(
                    model_name=model_name,
                    benchmark="Software Engineering Issues",
                    metric="percentage_resolved",
                    value=resolved_percent,
                    leaderboard_id=leaderboard_id,
                    higher_is_better=True,
                    scraped_at=datetime.now()
                )
                db.add(score_entry)
                total_score_entries += 1
                successful_integrations += 1
                
                # Show progress every 20 models
                if successful_integrations % 20 == 0:
                    print(f"  ✅ Processed {successful_integrations} models...")
                    
            except Exception as e:
                logger.warning(f"Error processing model {model_data}: {e}")
                continue
        
        # Commit all scores
        try:
            db.commit()
            print(f"\n🎉 SWE-Bench Integration Completed Successfully!")
            print(f"  📊 Models integrated: {successful_integrations}")
            print(f"  📈 Total score entries: {total_score_entries}")
            print(f"  📋 Leaderboard ID: {leaderboard_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error committing SWE-Bench scores: {e}")
            db.rollback()
            return False
    
    def verify_integration(self, db, leaderboard_id):
        """Verify the SWE-Bench integration was successful"""
        print(f"\n🔍 Verifying SWE-Bench integration...")
        
        # Count total scores
        total_scores = db.query(RawScore).filter_by(
            leaderboard_id=leaderboard_id
        ).count()
        
        # Count unique models
        unique_models = db.query(RawScore.model_name).filter_by(
            leaderboard_id=leaderboard_id
        ).distinct().count()
        
        # Get top 5 models by percentage resolved
        top_models = db.query(RawScore).filter_by(
            leaderboard_id=leaderboard_id,
            metric="percentage_resolved"
        ).order_by(RawScore.value.desc()).limit(5).all()
        
        print(f"📊 Verification Results:")
        print(f"  Total score entries: {total_scores}")
        print(f"  Unique models: {unique_models}")
        
        print(f"\n🏆 Top 5 Software Engineering Models:")
        for i, score in enumerate(top_models, 1):
            print(f"  {i}. {score.model_name}: {score.value:.1f}% resolved")
        
        return total_scores > 0 and unique_models > 0


def main():
    """Main integration function"""
    print("🚀 Starting SWE-Bench Verified Integration...")
    print("=" * 60)
    
    # Create database tables
    create_tables()
    
    # Create database session
    db = SessionLocal()
    
    integrator = SWEBenchIntegrator()
    
    try:
        # Step 1: Load SWE-Bench data
        if not integrator.load_swe_bench_data():
            print("❌ Failed to load SWE-Bench data")
            return False
        
        # Step 2: Create/get leaderboard
        leaderboard_id = integrator.create_or_get_leaderboard(db)
        if not leaderboard_id:
            print("❌ Failed to create/get SWE-Bench leaderboard")
            return False
        
        # Step 3: Integrate scores
        if not integrator.integrate_swe_bench_scores(db, leaderboard_id):
            print("❌ Failed to integrate SWE-Bench scores")
            return False
        
        # Step 4: Verify integration
        if not integrator.verify_integration(db, leaderboard_id):
            print("❌ Integration verification failed")
            return False
        
        print(f"\n🎉 SWE-BENCH INTEGRATION COMPLETED SUCCESSFULLY!")
        print(f"⚡ Software engineering capability added to Meta LLM platform")
        print(f"📊 {len(integrator.models_data)} models with coding evaluation data")
        print(f"🎯 Task 4.3 - Coding benchmark aggregation completed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Error during SWE-Bench integration: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 