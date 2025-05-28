#!/usr/bin/env python3
"""
Stanford HELM Integration Script
Loads Stanford HELM (Holistic Evaluation of Language Models) academic evaluation data into the database

Expected Data:
- 67 models from Stanford's academic research
- 16 comprehensive benchmarks (MMLU, BoolQ, TruthfulQA, HellaSwag, etc.)
- Mean win rate + individual benchmark scores
- Academic credibility and research-grade evaluation standards
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import json
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import our database models
from src.db.models import Base, RawScore, Leaderboard

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

class HELMIntegrator:
    def __init__(self, data_file: str = "helm_transformed_data_20250527_161217.json"):
        self.data_file = data_file
        self.leaderboard_name = "Stanford HELM Classic"
        self.leaderboard_category = "academic"
        self.models_data = []
        
    def load_helm_data(self):
        """Load the extracted HELM data from JSON file"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            self.models_data = data.get('models', [])
            extraction_info = data.get('extraction_info', {})
            
            print(f"📊 Loaded HELM data:")
            print(f"  Total models: {len(self.models_data)}")
            print(f"  Source: {extraction_info.get('source', 'Unknown')}")
            print(f"  Timestamp: {extraction_info.get('timestamp', 'Unknown')}")
            
            if not self.models_data:
                raise ValueError("No models data found in the file")
                
            return True
            
        except Exception as e:
            logger.error(f"Error loading HELM data: {e}")
            return False
    
    def create_or_get_leaderboard(self, db):
        """Create or get the HELM leaderboard entry"""
        # Check if leaderboard already exists
        existing_leaderboard = db.query(Leaderboard).filter_by(
            name=self.leaderboard_name
        ).first()
        
        if existing_leaderboard:
            print(f"📋 Found existing HELM leaderboard (ID: {existing_leaderboard.id})")
            return existing_leaderboard.id
        
        # Create new leaderboard
        new_leaderboard = Leaderboard(
            name=self.leaderboard_name,
            category=self.leaderboard_category
        )
        
        db.add(new_leaderboard)
        db.commit()
        db.refresh(new_leaderboard)
        
        print(f"✅ Created new HELM leaderboard (ID: {new_leaderboard.id})")
        return new_leaderboard.id
    
    def integrate_helm_scores(self, db, leaderboard_id):
        """Integrate all HELM model scores into the database"""
        print(f"\n🔄 Integrating HELM scores...")
        
        # Clear existing scores for this leaderboard (in case of re-run)
        deleted_count = db.query(RawScore).filter_by(
            leaderboard_id=leaderboard_id
        ).delete()
        
        if deleted_count > 0:
            print(f"🗑️ Cleared {deleted_count} existing HELM scores")
            db.commit()
        
        # Integration counters
        successful_integrations = 0
        total_score_entries = 0
        
        for model_data in self.models_data:
            model_name = model_data.get('model_name')
            mean_win_rate = model_data.get('mean_win_rate')
            benchmarks = model_data.get('benchmarks', {})
            
            if not model_name:
                logger.warning("Skipping model with no name")
                continue
                
            # Create score entry for mean win rate (overall performance)
            if mean_win_rate is not None:
                overall_score = RawScore(
                    model_name=model_name,
                    benchmark="Overall Performance",
                    metric="mean_win_rate",
                    value=mean_win_rate,
                    leaderboard_id=leaderboard_id,
                    higher_is_better=True,
                    scraped_at=datetime.now()
                )
                db.add(overall_score)
                total_score_entries += 1
            
            # Create score entries for individual benchmarks
            for benchmark_name, score in benchmarks.items():
                if score is not None:
                    # Get benchmark metadata
                    benchmark_meta = self._get_benchmark_metadata(benchmark_name)
                    
                    benchmark_score = RawScore(
                        model_name=model_name,
                        benchmark=benchmark_meta['full_name'],
                        metric=benchmark_meta['metric'],
                        value=score,
                        leaderboard_id=leaderboard_id,
                        higher_is_better=benchmark_meta['higher_is_better'],
                        scraped_at=datetime.now()
                    )
                    db.add(benchmark_score)
                    total_score_entries += 1
            
            successful_integrations += 1
            
            # Show progress every 10 models
            if successful_integrations % 10 == 0:
                print(f"  ✅ Processed {successful_integrations} models...")
        
        # Commit all scores
        try:
            db.commit()
            print(f"\n🎉 HELM Integration Completed Successfully!")
            print(f"  📊 Models integrated: {successful_integrations}")
            print(f"  📈 Total score entries: {total_score_entries}")
            print(f"  📋 Leaderboard ID: {leaderboard_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error committing HELM scores: {e}")
            db.rollback()
            return False
    
    def _get_benchmark_metadata(self, benchmark_name: str) -> dict:
        """Get metadata for HELM benchmarks"""
        benchmark_descriptions = {
            'mmlu': {
                'full_name': 'MMLU (Massive Multitask Language Understanding)',
                'metric': 'Exact Match',
                'higher_is_better': True
            },
            'boolq': {
                'full_name': 'BoolQ',
                'metric': 'Exact Match',
                'higher_is_better': True
            },
            'narrativeqa': {
                'full_name': 'NarrativeQA',
                'metric': 'F1 Score',
                'higher_is_better': True
            },
            'naturalquestions_closed': {
                'full_name': 'Natural Questions (Closed Book)',
                'metric': 'F1 Score',
                'higher_is_better': True
            },
            'naturalquestions_open': {
                'full_name': 'Natural Questions (Open Book)',
                'metric': 'F1 Score',
                'higher_is_better': True
            },
            'quac': {
                'full_name': 'QuAC (Question Answering in Context)',
                'metric': 'F1 Score',
                'higher_is_better': True
            },
            'hellaswag': {
                'full_name': 'HellaSwag',
                'metric': 'Exact Match',
                'higher_is_better': True
            },
            'openbookqa': {
                'full_name': 'OpenBookQA',
                'metric': 'Exact Match',
                'higher_is_better': True
            },
            'truthfulqa': {
                'full_name': 'TruthfulQA',
                'metric': 'Exact Match',
                'higher_is_better': True
            },
            'ms_marco_regular': {
                'full_name': 'MS MARCO (Regular Track)',
                'metric': 'RR@10',
                'higher_is_better': True
            },
            'ms_marco_trec': {
                'full_name': 'MS MARCO (TREC Track)',
                'metric': 'NDCG@10',
                'higher_is_better': True
            },
            'cnn_dailymail': {
                'full_name': 'CNN/DailyMail',
                'metric': 'ROUGE-2',
                'higher_is_better': True
            },
            'xsum': {
                'full_name': 'XSum',
                'metric': 'ROUGE-2',
                'higher_is_better': True
            },
            'imdb': {
                'full_name': 'IMDB Movie Reviews',
                'metric': 'Exact Match',
                'higher_is_better': True
            },
            'civilcomments': {
                'full_name': 'CivilComments',
                'metric': 'Exact Match',
                'higher_is_better': True
            },
            'raft': {
                'full_name': 'RAFT (Real-world Annotated Few-Shot)',
                'metric': 'Exact Match',
                'higher_is_better': True
            }
        }
        
        return benchmark_descriptions.get(benchmark_name, {
            'full_name': benchmark_name.upper(),
            'metric': 'Score',
            'higher_is_better': True
        })
    
    def verify_integration(self, db, leaderboard_id):
        """Verify the HELM integration was successful"""
        print(f"\n🔍 Verifying HELM integration...")
        
        # Count total scores
        total_scores = db.query(RawScore).filter_by(
            leaderboard_id=leaderboard_id
        ).count()
        
        # Count unique models
        unique_models = db.query(RawScore.model_name).filter_by(
            leaderboard_id=leaderboard_id
        ).distinct().count()
        
        # Count unique benchmarks
        unique_benchmarks = db.query(RawScore.benchmark).filter_by(
            leaderboard_id=leaderboard_id
        ).distinct().count()
        
        # Get top 5 models by mean win rate
        top_models = db.query(RawScore).filter_by(
            leaderboard_id=leaderboard_id,
            metric="mean_win_rate"
        ).order_by(RawScore.value.desc()).limit(5).all()
        
        print(f"📊 Verification Results:")
        print(f"  Total score entries: {total_scores}")
        print(f"  Unique models: {unique_models}")
        print(f"  Unique benchmarks: {unique_benchmarks}")
        print(f"  Average scores per model: {total_scores / unique_models:.1f}")
        
        print(f"\n🏆 Top 5 Models (by Mean Win Rate):")
        for i, score in enumerate(top_models, 1):
            print(f"  {i}. {score.model_name}: {score.value:.3f}")
        
        # Check some sample benchmark data
        mmlu_scores = db.query(RawScore).filter_by(
            leaderboard_id=leaderboard_id,
            benchmark="MMLU (Massive Multitask Language Understanding)"
        ).count()
        
        print(f"\n📈 Sample Benchmark Coverage:")
        print(f"  MMLU scores: {mmlu_scores}")
        
        return total_scores > 0 and unique_models > 0

def main():
    """Main integration function"""
    print("🎓 Starting Stanford HELM Integration...")
    print("=" * 60)
    
    # Create database tables
    create_tables()
    
    # Create database session
    db = SessionLocal()
    
    integrator = HELMIntegrator()
    
    try:
        # Step 1: Load HELM data
        if not integrator.load_helm_data():
            print("❌ Failed to load HELM data")
            return False
        
        # Step 2: Create/get leaderboard
        leaderboard_id = integrator.create_or_get_leaderboard(db)
        if not leaderboard_id:
            print("❌ Failed to create/get HELM leaderboard")
            return False
        
        # Step 3: Integrate scores
        if not integrator.integrate_helm_scores(db, leaderboard_id):
            print("❌ Failed to integrate HELM scores")
            return False
        
        # Step 4: Verify integration
        if not integrator.verify_integration(db, leaderboard_id):
            print("❌ Integration verification failed")
            return False
        
        print(f"\n🎉 HELM INTEGRATION COMPLETED SUCCESSFULLY!")
        print(f"🎓 Academic credibility added to Meta LLM platform")
        print(f"📊 67 models with comprehensive academic evaluation data")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Error during HELM integration: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 