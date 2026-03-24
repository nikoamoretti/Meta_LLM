"""
Automated Update System for Meta LLM Platform
Orchestrates scheduled updates across all data sources with smart change detection
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

from app.database import SessionLocal, engine
from db.db_models import Model, Benchmark, Score, Base
from scoring.normalise import z_score
from scoring.composite import category_composite, overall_composite

# Import all scrapers
from scrapers.arena_playwright_scraper import ArenaPlaywrightScraper
from scrapers.strawberry_bench_scraper import StrawberryBenchScraper
from scrapers.sources.huggingface_open_llm_scraper import HuggingFaceOpenLLMScraper
from scrapers.swe_bench_scraper import SWEBenchScraper
from scrapers.medical_llm_scraper import MedicalLLMScraper
from scrapers.legal_bench_final_scraper import LegalBenchFinalScraper
from scrapers.math_benchmark_scraper import MathBenchmarkScraper
from scrapers.multilingual_benchmark_scraper import MultilingualBenchmarkScraper
from scrapers.safety_alignment_scraper import SafetyAlignmentScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automated_updates.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UpdateFrequency(Enum):
    """Update frequency categories"""
    HIGH = "6h"      # 6 hours (Arena, Strawberry)
    MEDIUM = "12h"   # 12 hours
    DAILY = "24h"    # Daily (HuggingFace, SWE-Bench)
    WEEKLY = "7d"    # Weekly (HELM, Medical, Legal)

@dataclass
class DataSourceConfig:
    """Configuration for each data source"""
    name: str
    scraper_class: Any
    frequency: UpdateFrequency
    enabled: bool = True
    last_update: Optional[datetime] = None 
    last_hash: Optional[str] = None
    failure_count: int = 0
    max_failures: int = 3

@dataclass
class UpdateResult:
    """Result of an update operation"""
    source_name: str
    success: bool
    models_updated: int = 0
    scores_updated: int = 0
    new_models: int = 0
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    data_hash: Optional[str] = None

class AutomatedUpdateSystem:
    """Main automated update system orchestrator"""
    
    def __init__(self):
        self.scheduler = BlockingScheduler(
            executors={'default': ThreadPoolExecutor(max_workers=3)}
        )
        
        # Data source configurations with realistic update frequencies
        self.data_sources = {
            'chatbot_arena': DataSourceConfig(
                name='Chatbot Arena',
                scraper_class=ArenaPlaywrightScraper,
                frequency=UpdateFrequency.HIGH  # 6 hours - high activity
            ),
            'strawberry_bench': DataSourceConfig(
                name='Strawberry Bench', 
                scraper_class=StrawberryBenchScraper,
                frequency=UpdateFrequency.HIGH  # 6 hours - active reasoning leaderboard
            ),
            'huggingface_open_llm': DataSourceConfig(
                name='HuggingFace Open LLM',
                scraper_class=HuggingFaceOpenLLMScraper,
                frequency=UpdateFrequency.DAILY  # Daily - stable but active
            ),
            'swe_bench': DataSourceConfig(
                name='SWE-Bench Verified',
                scraper_class=SWEBenchScraper, 
                frequency=UpdateFrequency.DAILY  # Daily - coding evaluations
            ),
            'medical_llm': DataSourceConfig(
                name='Medical LLM',
                scraper_class=MedicalLLMScraper,
                frequency=UpdateFrequency.WEEKLY  # Weekly - slower domain updates
            ),
            'legal_bench': DataSourceConfig(
                name='Legal Bench',
                scraper_class=LegalBenchFinalScraper,
                frequency=UpdateFrequency.WEEKLY  # Weekly - legal domain updates
            ),
            'math_reasoning': DataSourceConfig(
                name='Math Reasoning Benchmarks',
                scraper_class=MathBenchmarkScraper,
                frequency=UpdateFrequency.WEEKLY  # Weekly - math benchmark updates
            ),
            'multilingual_evaluation': DataSourceConfig(
                name='Multilingual Evaluation',
                scraper_class=MultilingualBenchmarkScraper,
                frequency=UpdateFrequency.WEEKLY  # Weekly - multilingual benchmark updates
            ),
            'safety_alignment': DataSourceConfig(
                name='Safety & Alignment Benchmarks',
                scraper_class=SafetyAlignmentScraper,
                frequency=UpdateFrequency.DAILY  # Daily - safety is critical
            )
        }
        
        # Simple normalization will be done inline
        
        # Monitoring stats
        self.update_stats = {
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'last_update_time': None,
            'data_freshness_hours': {}
        }
        
        logger.info("AutomatedUpdateSystem initialized")
    
    def setup_scheduler(self):
        """Configure scheduled jobs for all data sources"""
        logger.info("Setting up scheduled jobs...")
        
        for source_key, config in self.data_sources.items():
            if not config.enabled:
                continue
                
            # Create appropriate trigger based on frequency
            if config.frequency == UpdateFrequency.HIGH:
                # Every 6 hours
                trigger = IntervalTrigger(hours=6)
                logger.info(f"Scheduling {config.name} every 6 hours")
            elif config.frequency == UpdateFrequency.MEDIUM:
                # Every 12 hours  
                trigger = IntervalTrigger(hours=12)
                logger.info(f"Scheduling {config.name} every 12 hours")
            elif config.frequency == UpdateFrequency.DAILY:
                # Daily at staggered times to avoid conflicts
                hours = {'huggingface_open_llm': 2, 'swe_bench': 4}.get(source_key, 6)
                trigger = CronTrigger(hour=hours, minute=0)
                logger.info(f"Scheduling {config.name} daily at {hours:02d}:00 UTC")
            elif config.frequency == UpdateFrequency.WEEKLY:
                # Weekly on different days
                days = {'medical_llm': 'tue', 'legal_bench': 'thu'}.get(source_key, 'sun')
                trigger = CronTrigger(day_of_week=days, hour=6, minute=0)
                logger.info(f"Scheduling {config.name} weekly on {days.capitalize()} at 06:00 UTC")
            
            # Add job to scheduler
            self.scheduler.add_job(
                func=self.update_data_source,
                trigger=trigger,
                args=[source_key],
                id=f'update_{source_key}',
                name=f'Update {config.name}',
                max_instances=1,  # Prevent overlapping runs
                coalesce=True,    # Combine missed runs
                misfire_grace_time=300  # 5 minute grace period
            )
        
        # Add system monitoring job (every hour)
        self.scheduler.add_job(
            func=self.monitor_system_health,
            trigger=IntervalTrigger(hours=1),
            id='system_monitor',
            name='System Health Monitor'
        )
        
        # Add daily composite score recalculation
        self.scheduler.add_job(
            func=self.recalculate_composite_scores,
            trigger=CronTrigger(hour=8, minute=0),  # 8 AM UTC daily
            id='composite_scores',
            name='Recalculate Composite Scores'
        )
        
        logger.info(f"Scheduled {len(self.data_sources)} data source jobs + 2 system jobs")
    
    def calculate_data_hash(self, data: Dict) -> str:
        """Calculate SHA-256 hash of data for change detection"""
        try:
            # Convert data to JSON string and hash
            data_str = json.dumps(data, sort_keys=True, default=str)
            return hashlib.sha256(data_str.encode()).hexdigest()
        except Exception as e:
            logger.warning(f"Error calculating hash: {e}")
            return f"error_{datetime.now().timestamp()}"
    
    def has_data_changed(self, source_key: str, new_data: Dict) -> bool:
        """Check if data has changed since last update"""
        config = self.data_sources[source_key]
        new_hash = self.calculate_data_hash(new_data)
        
        if config.last_hash is None:
            # First run, consider as changed
            config.last_hash = new_hash
            return True
        
        changed = new_hash != config.last_hash
        if changed:
            logger.info(f"{config.name}: Data has changed (hash: {new_hash[:8]}...)")
            config.last_hash = new_hash
        else:
            logger.info(f"{config.name}: No changes detected (hash: {new_hash[:8]}...)")
        
        return changed
    
    def update_data_source(self, source_key: str) -> UpdateResult:
        """Update a specific data source"""
        config = self.data_sources[source_key]
        start_time = datetime.now()
        
        logger.info(f"🔄 Starting update for {config.name}")
        
        try:
            # Initialize scraper
            scraper = config.scraper_class()
            
            # Scrape data
            raw_data = scraper.scrape_all()
            
            if not raw_data:
                raise Exception("No data returned from scraper")
            
            # Check if data has changed
            if not self.has_data_changed(source_key, raw_data):
                logger.info(f"⏭️  Skipping {config.name} - no changes detected")
                return UpdateResult(
                    source_name=config.name,
                    success=True,
                    execution_time=(datetime.now() - start_time).total_seconds()
                )
            
            # Process the data
            result = self.process_scraped_data(config.name, raw_data)
            
            # Update config
            config.last_update = datetime.now()
            config.failure_count = 0  # Reset on success
            
            # Update stats
            self.update_stats['total_updates'] += 1
            self.update_stats['successful_updates'] += 1
            self.update_stats['last_update_time'] = datetime.now()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            
            logger.info(f"✅ {config.name} update completed in {execution_time:.2f}s")
            logger.info(f"   Models: {result.models_updated}, Scores: {result.scores_updated}, New: {result.new_models}")
            
            return result
            
        except Exception as e:
            # Handle failure
            config.failure_count += 1
            self.update_stats['failed_updates'] += 1
            
            error_msg = str(e)
            logger.error(f"❌ {config.name} update failed: {error_msg}")
            
            # Disable source if too many failures
            if config.failure_count >= config.max_failures:
                config.enabled = False
                logger.error(f"🚫 Disabling {config.name} after {config.failure_count} failures")
                self.send_alert(f"Data source {config.name} disabled after repeated failures")
            
            return UpdateResult(
                source_name=config.name,
                success=False,
                error_message=error_msg,
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    
    def process_scraped_data(self, source_name: str, raw_data: Dict) -> UpdateResult:
        """Process scraped data and update database"""
        db = SessionLocal()
        models_updated = 0
        scores_updated = 0
        new_models = 0
        
        try:
            # Flatten data structure (handle nested categories)
            all_models = []
            for key, value in raw_data.items():
                if isinstance(value, list):
                    all_models.extend(value)
                elif isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, list):
                            all_models.extend(subvalue)
            
            logger.info(f"Processing {len(all_models)} models from {source_name}")
            
            for model_data in all_models:
                try:
                    # Get or create model
                    model = db.query(Model).filter(Model.name == model_data['model']).first()
                    if not model:
                        model = Model(
                            name=model_data['model'],
                            organization=model_data.get('organization', 'Unknown'),
                            created_at=datetime.utcnow()
                        )
                        db.add(model)
                        db.flush()
                        new_models += 1
                    
                    models_updated += 1
                    
                    # Process scores
                    scores = model_data.get('scores', {})
                    for metric_name, score_value in scores.items():
                        if score_value is None:
                            continue
                        
                        # Get or create benchmark
                        benchmark = db.query(Benchmark).filter(
                            Benchmark.name == metric_name
                        ).first()
                        
                        if not benchmark:
                            # Determine category from metric name
                            category = self.determine_benchmark_category(metric_name, source_name)
                            benchmark = Benchmark(
                                name=metric_name,
                                category=category,
                                description=f"{metric_name} from {source_name}"
                            )
                            db.add(benchmark)
                            db.flush()
                        
                        # Simple normalization (0-100 scale)
                        normalized_score = self.simple_normalize_score(
                            score_value, metric_name, source_name
                        )
                        
                        # Update or create score
                        score = db.query(Score).filter(
                            Score.model_id == model.id,
                            Score.benchmark_id == benchmark.id
                        ).first()
                        
                        if score:
                            score.value = score_value
                            score.normalized_value = normalized_score
                            score.source = source_name
                            score.updated_at = datetime.utcnow()
                        else:
                            score = Score(
                                model_id=model.id,
                                benchmark_id=benchmark.id,
                                value=score_value,
                                normalized_value=normalized_score,
                                source=source_name,
                                created_at=datetime.utcnow()
                            )
                            db.add(score)
                        
                        scores_updated += 1
                        
                except Exception as e:
                    logger.warning(f"Error processing model {model_data.get('model', 'unknown')}: {e}")
                    continue
            
            db.commit()
            
            return UpdateResult(
                source_name=source_name,
                success=True,
                models_updated=models_updated,
                scores_updated=scores_updated,
                new_models=new_models
            )
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def determine_benchmark_category(self, metric_name: str, source_name: str) -> str:
        """Determine benchmark category based on metric name and source"""
        metric_lower = metric_name.lower()
        source_lower = source_name.lower()
        
        # Source-based categorization
        if 'medical' in source_lower:
            return 'medical'
        elif 'legal' in source_lower:
            return 'legal'
        elif 'swe' in source_lower or 'code' in source_lower:
            return 'coding'
        elif 'arena' in source_lower:
            return 'general'
        elif 'strawberry' in source_lower:
            return 'reasoning'
        
        # Metric-based categorization
        if any(term in metric_lower for term in ['medical', 'health', 'clinical']):
            return 'medical'
        elif any(term in metric_lower for term in ['legal', 'law', 'jurisprudence']):
            return 'legal'
        elif any(term in metric_lower for term in ['code', 'programming', 'software']):
            return 'coding'
        elif any(term in metric_lower for term in ['math', 'mathematical', 'reasoning']):
            return 'reasoning'
        elif any(term in metric_lower for term in ['academic', 'research', 'scientific']):
            return 'academic'
        else:
            return 'general'
    
    def simple_normalize_score(self, value, metric_name: str, source_name: str) -> float:
        """Simple normalization to 0-100 scale"""
        try:
            # Handle different metric types
            metric_lower = metric_name.lower()
            
            # Arena scores (typically 800-1600)
            if 'arena' in source_name.lower() or 'score' in metric_lower:
                if 800 <= value <= 1600:
                    return min(100, max(0, ((value - 800) / 800) * 100))
            
            # Percentage scores (0-100)
            if any(term in metric_lower for term in ['accuracy', 'percent', '%', 'rate']):
                return min(100, max(0, value))
            
            # Math scores (typically 0-1 or 0-100)
            if 'math' in metric_lower:
                if 0 <= value <= 1:
                    return value * 100
                elif 0 <= value <= 100:
                    return value
            
            # Default: assume 0-100 range
            if 0 <= value <= 100:
                return value
            elif 0 <= value <= 1:
                return value * 100
            else:
                # For other ranges, normalize to 0-100
                return min(100, max(0, value))
                
        except (ValueError, TypeError):
            return 0.0
    
    def recalculate_composite_scores(self):
        """Recalculate composite scores for all models"""
        logger.info("🧮 Starting composite score recalculation...")
        
        try:
            db = SessionLocal()
            
            # Get all models
            models = db.query(Model).all()
            
            # Calculate simple overall composite for each model
            for model in models:
                # Get all normalized scores for this model
                scores = db.query(Score).filter(
                    Score.model_id == model.id,
                    Score.normalized_value.isnot(None)
                ).all()
                
                if scores:
                    # Simple average of all normalized scores
                    avg_score = sum(s.normalized_value for s in scores) / len(scores)
                    
                    # Get or create overall composite benchmark
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
                            source='Automated Composite',
                            created_at=datetime.utcnow()
                        )
                        db.add(overall_score)
            
            db.commit()
            logger.info(f"✅ Composite scores recalculated for {len(models)} models")
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Composite score recalculation failed: {e}")
            self.send_alert(f"Composite score recalculation failed: {e}")
        finally:
            db.close()
    
    def monitor_system_health(self):
        """Monitor system health and send alerts if needed"""
        logger.info("🔍 System health check...")
        
        # Check data freshness
        current_time = datetime.now()
        alerts = []
        
        for source_key, config in self.data_sources.items():
            if not config.enabled:
                continue
            
            if config.last_update:
                hours_since_update = (current_time - config.last_update).total_seconds() / 3600
                
                # Determine staleness threshold based on frequency
                thresholds = {
                    UpdateFrequency.HIGH: 12,    # 6h frequency, alert after 12h
                    UpdateFrequency.MEDIUM: 24,  # 12h frequency, alert after 24h
                    UpdateFrequency.DAILY: 48,   # 24h frequency, alert after 48h
                    UpdateFrequency.WEEKLY: 168  # 7d frequency, alert after 10d
                }
                
                threshold = thresholds.get(config.frequency, 24)
                
                if hours_since_update > threshold:
                    alerts.append(f"{config.name}: {hours_since_update:.1f}h since last update")
                
                # Update stats
                self.update_stats['data_freshness_hours'][source_key] = hours_since_update
        
        # Send alerts if any
        if alerts:
            alert_message = "Data freshness alerts:\n" + "\n".join(alerts)
            logger.warning(alert_message)
            self.send_alert(alert_message)
        
        # Check success rate
        if self.update_stats['total_updates'] > 0:
            success_rate = (self.update_stats['successful_updates'] / 
                          self.update_stats['total_updates']) * 100
            
            if success_rate < 95:  # Below target
                self.send_alert(f"Update success rate below target: {success_rate:.1f}%")
        
        logger.info("✅ System health check completed")
    
    def send_alert(self, message: str):
        """Send alert (placeholder for email/Slack integration)"""
        logger.critical(f"🚨 ALERT: {message}")
        
        # TODO: Implement actual alerting (email, Slack, etc.)
        # For now, just log critically
        
        # In production, this would integrate with:
        # - Email notifications
        # - Slack webhooks  
        # - PagerDuty/alerting systems
        # - Dashboard notifications
    
    def get_system_status(self) -> Dict:
        """Get current system status for monitoring dashboard"""
        return {
            'stats': self.update_stats,
            'sources': {
                key: {
                    'name': config.name,
                    'enabled': config.enabled,
                    'frequency': config.frequency.value,
                    'last_update': config.last_update.isoformat() if config.last_update else None,
                    'failure_count': config.failure_count,
                    'hours_since_update': (
                        (datetime.now() - config.last_update).total_seconds() / 3600 
                        if config.last_update else None
                    )
                }
                for key, config in self.data_sources.items()
            },
            'last_check': datetime.now().isoformat()
        }
    
    def start(self):
        """Start the automated update system"""
        logger.info("🚀 Starting Meta LLM Automated Update System")
        
        # Setup jobs
        self.setup_scheduler()
        
        # Start scheduler
        try:
            logger.info("Scheduler started. Press Ctrl+C to stop.")
            self.scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            self.scheduler.shutdown()
            logger.info("Scheduler stopped.")

def main():
    """Main entry point"""
    # Create tables if needed
    Base.metadata.create_all(bind=engine)
    
    # Initialize and start system
    update_system = AutomatedUpdateSystem()
    update_system.start()

if __name__ == "__main__":
    main() 