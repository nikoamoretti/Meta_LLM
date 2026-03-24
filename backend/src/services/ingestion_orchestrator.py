"""
Unified Data Ingestion Orchestrator
Manages all 7 master sources with scheduling, monitoring, and error handling
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import traceback

from sqlalchemy.orm import Session
from ..db.models import get_db
from ..db.registry_models import ModelRegistry, MasterModel
from ..db.registry_benchmarks import BenchmarkRegistry, MasterBenchmark
from ..scrapers.huggingface_hub_scraper import HuggingFaceHubScraper
from ..scrapers.huggingface_csv_scraper import HuggingFaceCSVScraper
from ..scrapers.chatbot_arena_scraper import ChatbotArenaScraper
from ..scrapers.openrouter_scraper import OpenRouterScraper
from ..scrapers.scale_seal_scraper import ScaleSEALScraper
from ..scrapers.klu_scraper import KluScraper
from ..scrapers.huggingface_spaces_scraper import HuggingFaceSpacesScraper
from ..scrapers.paperswithcode_scraper import PapersWithCodeScraper

logger = logging.getLogger(__name__)

class SourceType(Enum):
    """Classification of data sources by update frequency"""
    API_DAILY = "api_daily"        # APIs updated daily
    WEB_WEEKLY = "web_weekly"      # Web scraping weekly
    CSV_DAILY = "csv_daily"        # CSV feeds daily

@dataclass
class SourceConfig:
    """Configuration for each data source"""
    name: str
    scraper_class: type
    source_type: SourceType
    priority: int  # 1=highest, 5=lowest
    timeout_minutes: int = 30
    retry_attempts: int = 3
    required_fields: List[str] = None
    
@dataclass 
class IngestionResult:
    """Result of a single source ingestion"""
    source_name: str
    success: bool
    models_found: int
    models_new: int
    benchmarks_found: int
    benchmarks_new: int
    scores_ingested: int
    duration_seconds: float
    error_message: Optional[str] = None
    warnings: List[str] = None

class IngestionOrchestrator:
    """
    Orchestrates all data ingestion from the 7 master sources
    """
    
    def __init__(self):
        self.sources = self._configure_sources()
        self.results_cache = {}
        
    def _configure_sources(self) -> Dict[str, SourceConfig]:
        """Configure all 7 master data sources"""
        return {
            # Daily API sources (05:00 UTC)
            "huggingface_hub": SourceConfig(
                name="HuggingFace Hub",
                scraper_class=HuggingFaceHubScraper,
                source_type=SourceType.API_DAILY,
                priority=1,
                timeout_minutes=45,
                required_fields=["model_id", "downloads", "likes"]
            ),
            
            "huggingface_open_llm_csv": SourceConfig(
                name="HuggingFace Open-LLM CSV",
                scraper_class=HuggingFaceCSVScraper,
                source_type=SourceType.CSV_DAILY,
                priority=1,
                timeout_minutes=15,
                required_fields=["model", "score"]
            ),
            
            "chatbot_arena_csv": SourceConfig(
                name="Chatbot Arena CSV",
                scraper_class=ChatbotArenaScraper,
                source_type=SourceType.CSV_DAILY,
                priority=1,
                timeout_minutes=20,
                required_fields=["model", "elo"]
            ),
            
            "openrouter_api": SourceConfig(
                name="OpenRouter API",
                scraper_class=OpenRouterScraper,
                source_type=SourceType.API_DAILY,
                priority=2,
                timeout_minutes=10,
                required_fields=["id", "name"]
            ),
            
            "huggingface_spaces": SourceConfig(
                name="HuggingFace Spaces (leaderboard tag)",
                scraper_class=HuggingFaceSpacesScraper,
                source_type=SourceType.API_DAILY,
                priority=3,
                timeout_minutes=60,
                required_fields=["space_id", "models"]
            ),
            
            # Weekly web scraping sources (Wed 04:00 UTC)
            "scale_seal": SourceConfig(
                name="Scale SEAL Table",
                scraper_class=ScaleSEALScraper,
                source_type=SourceType.WEB_WEEKLY,
                priority=2,
                timeout_minutes=30,
                required_fields=["model", "score"]
            ),
            
            "paperswithcode": SourceConfig(
                name="PapersWithCode SOTA",
                scraper_class=PapersWithCodeScraper,
                source_type=SourceType.WEB_WEEKLY,
                priority=4,
                timeout_minutes=90,
                required_fields=["model", "benchmark", "score"]
            )
        }
    
    async def run_daily_ingestion(self) -> Dict[str, IngestionResult]:
        """
        Run daily ingestion (05:00 UTC) - APIs and CSV feeds
        """
        logger.info("Starting daily ingestion cycle")
        
        daily_sources = [
            name for name, config in self.sources.items() 
            if config.source_type in [SourceType.API_DAILY, SourceType.CSV_DAILY]
        ]
        
        return await self._run_ingestion_batch(daily_sources)
    
    async def run_weekly_ingestion(self) -> Dict[str, IngestionResult]:
        """
        Run weekly ingestion (Wed 04:00 UTC) - web scraping
        """
        logger.info("Starting weekly ingestion cycle")
        
        weekly_sources = [
            name for name, config in self.sources.items()
            if config.source_type == SourceType.WEB_WEEKLY
        ]
        
        return await self._run_ingestion_batch(weekly_sources)
    
    async def run_full_ingestion(self) -> Dict[str, IngestionResult]:
        """
        Run complete ingestion of all sources (for testing/recovery)
        """
        logger.info("Starting full ingestion cycle")
        
        all_sources = list(self.sources.keys())
        return await self._run_ingestion_batch(all_sources)
    
    async def _run_ingestion_batch(self, source_names: List[str]) -> Dict[str, IngestionResult]:
        """
        Run ingestion for a batch of sources in priority order
        """
        results = {}
        
        # Sort by priority
        sorted_sources = sorted(
            source_names,
            key=lambda name: self.sources[name].priority
        )
        
        for source_name in sorted_sources:
            logger.info(f"Starting ingestion for: {source_name}")
            
            try:
                result = await self._ingest_single_source(source_name)
                results[source_name] = result
                
                if result.success:
                    logger.info(f"✅ {source_name}: {result.models_found} models, {result.scores_ingested} scores")
                else:
                    logger.error(f"❌ {source_name}: {result.error_message}")
                    
            except Exception as e:
                logger.error(f"💥 {source_name} crashed: {str(e)}")
                results[source_name] = IngestionResult(
                    source_name=source_name,
                    success=False,
                    models_found=0,
                    models_new=0,
                    benchmarks_found=0,
                    benchmarks_new=0,
                    scores_ingested=0,
                    duration_seconds=0,
                    error_message=f"Orchestrator error: {str(e)}"
                )
        
        # Cache results for monitoring
        self.results_cache[datetime.utcnow().isoformat()] = results
        
        return results
    
    async def _ingest_single_source(self, source_name: str) -> IngestionResult:
        """
        Ingest data from a single source with error handling and retries
        """
        config = self.sources[source_name]
        start_time = datetime.utcnow()
        
        for attempt in range(config.retry_attempts):
            try:
                # Initialize database session and registries
                with next(get_db()) as session:
                    model_registry = ModelRegistry(session)
                    benchmark_registry = BenchmarkRegistry(session)
                    
                    # Initialize scraper
                    scraper = config.scraper_class()
                    
                    # Perform scraping with timeout
                    raw_data = await asyncio.wait_for(
                        scraper.scrape_async(),
                        timeout=config.timeout_minutes * 60
                    )
                    
                    # Validate required fields
                    if config.required_fields:
                        self._validate_data_structure(raw_data, config.required_fields)
                    
                    # Process the data
                    result = await self._process_scraped_data(
                        raw_data, 
                        source_name, 
                        model_registry, 
                        benchmark_registry,
                        session
                    )
                    
                    # Commit transaction
                    session.commit()
                    
                    # Calculate duration
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    result.duration_seconds = duration
                    
                    return result
                    
            except asyncio.TimeoutError:
                error_msg = f"Timeout after {config.timeout_minutes} minutes"
                logger.warning(f"{source_name} attempt {attempt + 1}: {error_msg}")
                
                if attempt == config.retry_attempts - 1:
                    return IngestionResult(
                        source_name=source_name,
                        success=False,
                        models_found=0,
                        models_new=0,
                        benchmarks_found=0,
                        benchmarks_new=0,
                        scores_ingested=0,
                        duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                        error_message=error_msg
                    )
                    
                await asyncio.sleep(30 * (attempt + 1))  # Exponential backoff
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                logger.error(f"{source_name} attempt {attempt + 1}: {error_msg}")
                logger.debug(traceback.format_exc())
                
                if attempt == config.retry_attempts - 1:
                    return IngestionResult(
                        source_name=source_name,
                        success=False,
                        models_found=0,
                        models_new=0,
                        benchmarks_found=0,
                        benchmarks_new=0,
                        scores_ingested=0,
                        duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                        error_message=error_msg
                    )
                    
                await asyncio.sleep(15 * (attempt + 1))
    
    async def _process_scraped_data(
        self, 
        raw_data: dict, 
        source_name: str,
        model_registry: ModelRegistry,
        benchmark_registry: BenchmarkRegistry,
        session: Session
    ) -> IngestionResult:
        """
        Process scraped data into the registries
        """
        models_found = 0
        models_new = 0
        benchmarks_found = 0
        benchmarks_new = 0
        scores_ingested = 0
        warnings = []
        
        # Process models
        if 'models' in raw_data:
            for model_data in raw_data['models']:
                try:
                    # Check if this is a new model
                    existing = model_registry.find_model_by_name(model_data['name'])
                    if not existing:
                        models_new += 1
                    
                    # Register model
                    model = model_registry.register_model(
                        raw_name=model_data['name'],
                        source_tag=source_name,
                        **model_data.get('metadata', {})
                    )
                    models_found += 1
                    
                except Exception as e:
                    warnings.append(f"Model registration failed: {model_data.get('name', 'unknown')} - {str(e)}")
        
        # Process benchmarks and scores
        if 'leaderboard' in raw_data:
            # Auto-discover benchmarks from column headers
            discovered = benchmark_registry.auto_discover_from_leaderboard(
                raw_data['leaderboard'], 
                source_name
            )
            benchmarks_new += len(discovered)
            
            # Process scores
            for entry in raw_data['leaderboard'].get('entries', []):
                try:
                    # Ensure model exists
                    model = model_registry.register_model(
                        raw_name=entry['model'],
                        source_tag=source_name
                    )
                    
                    # Process each benchmark score
                    for benchmark_name, score_value in entry.get('scores', {}).items():
                        if score_value is not None:
                            # Ensure benchmark exists
                            benchmark = benchmark_registry.register_benchmark(benchmark_name)
                            benchmarks_found += 1
                            
                            # Create raw score entry
                            from ..db.models import RawScore
                            raw_score = RawScore(
                                model_name=model.model_id,
                                benchmark=benchmark.benchmark_id,
                                metric=benchmark.unit.value,
                                value=float(score_value),
                                source=source_name,
                                scraped_at=datetime.utcnow()
                            )
                            session.add(raw_score)
                            scores_ingested += 1
                            
                except Exception as e:
                    warnings.append(f"Score ingestion failed: {entry.get('model', 'unknown')} - {str(e)}")
        
        return IngestionResult(
            source_name=source_name,
            success=True,
            models_found=models_found,
            models_new=models_new,
            benchmarks_found=benchmarks_found,
            benchmarks_new=benchmarks_new,
            scores_ingested=scores_ingested,
            duration_seconds=0,  # Will be set by caller
            warnings=warnings if warnings else None
        )
    
    def _validate_data_structure(self, data: dict, required_fields: List[str]):
        """
        Validate that scraped data has required structure
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        
        # For now, just check that data is not empty
        if not data:
            raise ValueError("Data is empty")
        
        # Additional validation could be added here
        
    def get_ingestion_statistics(self) -> dict:
        """
        Get ingestion statistics and health metrics
        """
        # Get recent results (last 7 days)
        recent_results = {}
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        for timestamp, results in self.results_cache.items():
            if datetime.fromisoformat(timestamp) > cutoff:
                recent_results[timestamp] = results
        
        # Calculate success rates
        source_stats = {}
        for source_name in self.sources.keys():
            runs = []
            for results in recent_results.values():
                if source_name in results:
                    runs.append(results[source_name])
            
            if runs:
                success_rate = sum(1 for r in runs if r.success) / len(runs)
                avg_duration = sum(r.duration_seconds for r in runs) / len(runs)
                total_models = sum(r.models_found for r in runs)
                total_scores = sum(r.scores_ingested for r in runs)
                
                source_stats[source_name] = {
                    "runs_last_7_days": len(runs),
                    "success_rate": round(success_rate * 100, 1),
                    "avg_duration_seconds": round(avg_duration, 1),
                    "total_models_found": total_models,
                    "total_scores_ingested": total_scores,
                    "last_run": max(runs, key=lambda r: r.duration_seconds) if runs else None
                }
        
        return {
            "source_statistics": source_stats,
            "total_sources": len(self.sources),
            "last_daily_run": None,  # Would track from scheduler
            "last_weekly_run": None,  # Would track from scheduler
            "next_scheduled_run": None  # Would calculate from schedule
        }
    
    async def test_single_source(self, source_name: str) -> IngestionResult:
        """
        Test ingestion from a single source (for debugging)
        """
        if source_name not in self.sources:
            raise ValueError(f"Unknown source: {source_name}")
        
        logger.info(f"Testing ingestion for: {source_name}")
        return await self._ingest_single_source(source_name)
    
    def check_deprecations(self) -> dict:
        """
        Check for models that should be deprecated
        """
        with next(get_db()) as session:
            model_registry = ModelRegistry(session)
            deprecated = model_registry.check_deprecations()
            session.commit()
            
            return {
                "deprecated_count": len(deprecated),
                "deprecated_models": deprecated,
                "deprecation_criteria": "Absent from all sources for 180+ days AND < 5 scores"
            }

# Global orchestrator instance
orchestrator = IngestionOrchestrator()