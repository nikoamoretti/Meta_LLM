"""
Simple job - just update the database with working scrapers
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from db.db_models import Model, Benchmark, Score, Base
from scrapers.simple_scraper import SimpleScraper
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_score(value, metric):
    """Simple normalization to 0-100"""
    if metric in ['arc', 'hellaswag', 'mmlu', 'truthfulqa', 'winogrande', 'gsm8k', 'average', 'win_rate']:
        return min(100, max(0, value))  # Already 0-100
    elif metric == 'context_length':
        # Normalize context length (4k = 50, 128k = 100)
        return min(100, max(0, (value / 128000) * 100))
    elif metric == 'cost_per_million':
        # Invert cost (lower is better) - $0 = 100, $100 = 0
        return max(0, 100 - value)
    else:
        return value

def run_job():
    """Main job function"""
    logger.info("Starting simple job...")
    
    # Create tables if needed
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Get data from simple scraper
        scraper = SimpleScraper()
        all_data = scraper.scrape_all()
        
        # Process each source
        for source_name, models in all_data.items():
            logger.info(f"Processing {len(models)} models from {source_name}")
            
            for model_data in models:
                # Get or create model
                model = db.query(Model).filter(Model.name == model_data['model']).first()
                if not model:
                    model = Model(
                        name=model_data['model'],
                        organization='Unknown',
                        created_at=datetime.utcnow()
                    )
                    db.add(model)
                    db.flush()
                
                # Store scores
                for metric, value in model_data['scores'].items():
                    if value is None or metric == 'total_battles':
                        continue
                    
                    # Get or create benchmark
                    benchmark = db.query(Benchmark).filter(
                        Benchmark.name == metric
                    ).first()
                    
                    if not benchmark:
                        benchmark = Benchmark(
                            name=metric,
                            category='general',
                            description=f"{metric} benchmark"
                        )
                        db.add(benchmark)
                        db.flush()
                    
                    # Update or create score
                    score = db.query(Score).filter(
                        Score.model_id == model.id,
                        Score.benchmark_id == benchmark.id
                    ).first()
                    
                    normalized = normalize_score(value, metric)
                    
                    if score:
                        score.value = value
                        score.normalized_value = normalized
                        score.updated_at = datetime.utcnow()
                    else:
                        score = Score(
                            model_id=model.id,
                            benchmark_id=benchmark.id,
                            value=value,
                            normalized_value=normalized,
                            source=source_name,
                            created_at=datetime.utcnow()
                        )
                        db.add(score)
        
        # Calculate overall scores
        logger.info("Calculating overall scores...")
        all_models = db.query(Model).all()
        
        overall_benchmark = db.query(Benchmark).filter(
            Benchmark.name == 'overall_composite'
        ).first()
        
        if not overall_benchmark:
            overall_benchmark = Benchmark(
                name='overall_composite',
                category='composite',
                description='Overall composite score'
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
                # Simple average of all normalized scores
                avg_score = sum(s.normalized_value for s in scores) / len(scores)
                
                # Update or create overall score
                overall_score = db.query(Score).filter(
                    Score.model_id == model.id,
                    Score.benchmark_id == overall_benchmark.id
                ).first()
                
                if overall_score:
                    overall_score.value = avg_score
                    overall_score.normalized_value = avg_score
                    overall_score.updated_at = datetime.utcnow()
                else:
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

if __name__ == "__main__":
    run_job() 