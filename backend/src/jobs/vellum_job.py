"""
Vellum-only job - clean, focused data from Vellum AI leaderboard
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from db.db_models import Model, Benchmark, Score, Base
from scrapers.vellum_scraper import VellumScraper
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_score(value, metric):
    """Normalize scores to 0-100 scale"""
    # Most Vellum metrics are already percentages
    if metric in ['gpqa_diamond', 'aime_2025', 'swe_bench', 'bfcl', 'grind']:
        return min(100, max(0, value))  # Already 0-100
    elif metric == 'humanity_last_exam':
        # This is a very hard benchmark, scores are low (0-50 range)
        # Normalize to 0-100 by doubling
        return min(100, max(0, value * 2))
    else:
        return value

def clear_old_data(db):
    """Clear old data to start fresh"""
    logger.info("Clearing old data...")
    db.query(Score).delete()
    db.query(Benchmark).delete()
    db.query(Model).delete()
    db.commit()

def run_job():
    """Main job function"""
    logger.info("Starting Vellum-only job...")
    
    # Create tables if needed
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Clear old data for clean start
        clear_old_data(db)
        
        # Get data from Vellum scraper
        scraper = VellumScraper()
        all_data = scraper.scrape_all()
        
        # Process Vellum data
        vellum_models = all_data.get('vellum', [])
        logger.info(f"Processing {len(vellum_models)} models from Vellum AI")
        
        for model_data in vellum_models:
            # Get or create model
            model = Model(
                name=model_data['model'],
                organization='Unknown',
                created_at=datetime.utcnow()
            )
            db.add(model)
            db.flush()
            
            # Store scores
            for metric, value in model_data['scores'].items():
                if value is None:
                    continue
                
                # Get or create benchmark
                benchmark = db.query(Benchmark).filter(
                    Benchmark.name == metric
                ).first()
                
                if not benchmark:
                    benchmark = Benchmark(
                        name=metric,
                        category=get_category_for_metric(metric),
                        description=f"{metric} benchmark from Vellum AI"
                    )
                    db.add(benchmark)
                    db.flush()
                
                # Create score
                normalized = normalize_score(value, metric)
                
                score = Score(
                    model_id=model.id,
                    benchmark_id=benchmark.id,
                    value=value,
                    normalized_value=normalized,
                    source='Vellum AI',
                    created_at=datetime.utcnow()
                )
                db.add(score)
        
        # Calculate overall scores
        logger.info("Calculating overall scores...")
        all_models = db.query(Model).all()
        
        # Create overall benchmark
        overall_benchmark = Benchmark(
            name='overall_composite',
            category='composite',
            description='Overall composite score from Vellum benchmarks'
        )
        db.add(overall_benchmark)
        db.flush()
        
        for model in all_models:
            # Get all normalized scores for this model
            scores = db.query(Score).filter(
                Score.model_id == model.id,
                Score.benchmark_id != overall_benchmark.id
            ).all()
            
            if scores:
                # Weighted average - give more weight to comprehensive benchmarks
                weights = {
                    'gpqa_diamond': 1.5,  # Reasoning is important
                    'aime_2025': 1.2,     # Math reasoning
                    'swe_bench': 1.5,     # Coding is important
                    'bfcl': 1.0,          # Tool use
                    'grind': 1.3,         # Adaptive reasoning
                    'humanity_last_exam': 2.0  # Most comprehensive benchmark
                }
                
                weighted_sum = 0
                total_weight = 0
                
                for score in scores:
                    benchmark_name = db.query(Benchmark).filter(Benchmark.id == score.benchmark_id).first().name
                    weight = weights.get(benchmark_name, 1.0)
                    weighted_sum += score.normalized_value * weight
                    total_weight += weight
                
                avg_score = weighted_sum / total_weight if total_weight > 0 else 0
                
                # Create overall score
                overall_score = Score(
                    model_id=model.id,
                    benchmark_id=overall_benchmark.id,
                    value=avg_score,
                    normalized_value=avg_score,
                    source='Calculated',
                    created_at=datetime.utcnow()
                )
                db.add(overall_score)
        
        db.commit()
        
        # Summary
        total_models = db.query(Model).count()
        total_scores = db.query(Score).count()
        logger.info(f"Job complete! Models: {total_models}, Scores: {total_scores}")
        
    except Exception as e:
        logger.error(f"Job failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def get_category_for_metric(metric):
    """Map metrics to categories"""
    category_map = {
        'gpqa_diamond': 'reasoning',
        'aime_2025': 'math',
        'swe_bench': 'code',
        'bfcl': 'tool_use',
        'grind': 'reasoning',
        'humanity_last_exam': 'general'
    }
    return category_map.get(metric, 'general')

if __name__ == "__main__":
    run_job() 