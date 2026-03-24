"""
Data Quality Monitoring and Acceptance Testing System
Ensures data integrity, completeness, and accuracy across all sources
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

from ..db.models import get_db, RawScore, NormalizedScore
from ..db.registry_models import MasterModel, ModelRegistry
from ..db.registry_benchmarks import MasterBenchmark, BenchmarkRegistry, BenchmarkCategory
from ..services.ingestion_orchestrator import orchestrator

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class QualityAlert:
    level: AlertLevel
    title: str
    description: str
    timestamp: datetime
    source: str
    data: Optional[Dict] = None

@dataclass
class AcceptanceTestResult:
    test_name: str
    passed: bool
    threshold: float
    actual_value: float
    message: str
    timestamp: datetime

class QualityMonitor:
    """
    Comprehensive data quality monitoring system
    """
    
    def __init__(self):
        self.alerts = []
        self.test_results = []
        
        # Alert thresholds
        self.thresholds = {
            "min_daily_models": 10,
            "min_daily_scores": 100,
            "max_failure_rate": 0.2,  # 20%
            "min_arena_top100_coverage": 0.95,  # 95%
            "min_hf_trending_coverage": 0.95,  # 95%
            "max_nan_scores": 0.01,  # 1%
            "min_confidence_score": 0.7,
            "max_source_downtime_hours": 48
        }
    
    async def run_quality_checks(self) -> Dict:
        """
        Run comprehensive quality checks
        """
        logger.info("Starting data quality checks...")
        
        start_time = datetime.utcnow()
        
        # Run all quality checks
        checks = [
            self._check_daily_ingestion_volume(),
            self._check_source_health(),
            self._check_arena_coverage(),
            self._check_huggingface_coverage(),
            self._check_data_freshness(),
            self._check_normalization_quality(),
            self._check_model_registry_integrity(),
            self._check_benchmark_coverage(),
            self._check_duplicate_detection(),
            self._check_score_distribution()
        ]
        
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        # Compile results
        passed_checks = 0
        failed_checks = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Quality check {i} failed with exception: {str(result)}")
                failed_checks += 1
                self._add_alert(
                    AlertLevel.ERROR,
                    f"Quality Check {i} Failed",
                    f"Exception: {str(result)}",
                    "quality_monitor"
                )
            elif isinstance(result, bool):
                if result:
                    passed_checks += 1
                else:
                    failed_checks += 1
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Generate summary
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "duration_seconds": duration,
            "total_checks": len(checks),
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "success_rate": passed_checks / len(checks) if checks else 0,
            "alerts": [self._alert_to_dict(alert) for alert in self.alerts[-10:]],  # Last 10 alerts
            "test_results": [self._test_result_to_dict(result) for result in self.test_results[-20:]]  # Last 20 tests
        }
        
        # Send alerts if needed
        if failed_checks > 0:
            await self._send_alerts()
        
        logger.info(f"Quality checks complete: {passed_checks}/{len(checks)} passed")
        
        return summary
    
    async def _check_daily_ingestion_volume(self) -> bool:
        """
        Check that we're ingesting sufficient data daily
        """
        logger.info("Checking daily ingestion volume...")
        
        with next(get_db()) as session:
            # Check models added in last 24 hours
            yesterday = datetime.utcnow() - timedelta(hours=24)
            
            new_models = session.query(func.count(MasterModel.model_id)).filter(
                MasterModel.first_seen >= yesterday
            ).scalar()
            
            # Check scores added in last 24 hours
            new_scores = session.query(func.count(RawScore.id)).filter(
                RawScore.scraped_at >= yesterday
            ).scalar()
            
            # Test against thresholds
            models_passed = new_models >= self.thresholds["min_daily_models"]
            scores_passed = new_scores >= self.thresholds["min_daily_scores"]
            
            self._add_test_result(
                "daily_model_volume",
                models_passed,
                self.thresholds["min_daily_models"],
                new_models,
                f"Found {new_models} new models in last 24h"
            )
            
            self._add_test_result(
                "daily_score_volume", 
                scores_passed,
                self.thresholds["min_daily_scores"],
                new_scores,
                f"Found {new_scores} new scores in last 24h"
            )
            
            if not models_passed:
                self._add_alert(
                    AlertLevel.WARNING,
                    "Low Daily Model Volume",
                    f"Only {new_models} models added in last 24h (threshold: {self.thresholds['min_daily_models']})",
                    "ingestion_monitor"
                )
            
            if not scores_passed:
                self._add_alert(
                    AlertLevel.WARNING,
                    "Low Daily Score Volume", 
                    f"Only {new_scores} scores added in last 24h (threshold: {self.thresholds['min_daily_scores']})",
                    "ingestion_monitor"
                )
            
            return models_passed and scores_passed
    
    async def _check_source_health(self) -> bool:
        """
        Check health of all ingestion sources
        """
        logger.info("Checking source health...")
        
        # Get recent ingestion statistics
        stats = orchestrator.get_ingestion_statistics()
        
        failed_sources = []
        
        for source_name, source_stats in stats.get("source_statistics", {}).items():
            success_rate = source_stats.get("success_rate", 0) / 100
            
            if success_rate < (1 - self.thresholds["max_failure_rate"]):
                failed_sources.append(source_name)
                
                self._add_alert(
                    AlertLevel.ERROR,
                    f"Source Health Issue: {source_name}",
                    f"Success rate: {success_rate:.1%} (threshold: {1-self.thresholds['max_failure_rate']:.1%})",
                    "source_monitor"
                )
        
        passed = len(failed_sources) == 0
        
        self._add_test_result(
            "source_health",
            passed,
            1 - self.thresholds["max_failure_rate"],
            1 - (len(failed_sources) / len(stats.get("source_statistics", {}))),
            f"Failed sources: {failed_sources}" if failed_sources else "All sources healthy"
        )
        
        return passed
    
    async def _check_arena_coverage(self) -> bool:
        """
        Check coverage of Chatbot Arena top 100 models
        """
        logger.info("Checking Arena top-100 coverage...")
        
        # This would require fetching current Arena top 100
        # For now, simulate the check
        
        with next(get_db()) as session:
            model_registry = ModelRegistry(session)
            
            # Get models that likely came from Arena (simplified check)
            arena_models = session.query(MasterModel).filter(
                or_(
                    MasterModel.source_tag == "chatbot_arena",
                    MasterModel.model_id.contains("gpt"),
                    MasterModel.model_id.contains("claude"),
                    MasterModel.model_id.contains("gemini")
                )
            ).count()
            
            # Estimate coverage (this would be more precise with actual Arena data)
            estimated_coverage = min(arena_models / 100, 1.0)
            
            passed = estimated_coverage >= self.thresholds["min_arena_top100_coverage"]
            
            self._add_test_result(
                "arena_top100_coverage",
                passed,
                self.thresholds["min_arena_top100_coverage"],
                estimated_coverage,
                f"Estimated {estimated_coverage:.1%} coverage of Arena top-100"
            )
            
            if not passed:
                self._add_alert(
                    AlertLevel.WARNING,
                    "Low Arena Coverage",
                    f"Arena top-100 coverage: {estimated_coverage:.1%} (threshold: {self.thresholds['min_arena_top100_coverage']:.1%})",
                    "coverage_monitor"
                )
            
            return passed
    
    async def _check_huggingface_coverage(self) -> bool:
        """
        Check coverage of HuggingFace trending models
        """
        logger.info("Checking HuggingFace trending coverage...")
        
        with next(get_db()) as session:
            # Get models from HuggingFace
            hf_models = session.query(MasterModel).filter(
                or_(
                    MasterModel.source_tag == "huggingface_hub",
                    MasterModel.huggingface_id.isnot(None)
                )
            ).count()
            
            # Estimate coverage of trending models
            estimated_coverage = min(hf_models / 50, 1.0)  # Assume top 50 trending
            
            passed = estimated_coverage >= self.thresholds["min_hf_trending_coverage"]
            
            self._add_test_result(
                "hf_trending_coverage",
                passed,
                self.thresholds["min_hf_trending_coverage"],
                estimated_coverage,
                f"Estimated {estimated_coverage:.1%} coverage of HF trending"
            )
            
            return passed
    
    async def _check_data_freshness(self) -> bool:
        """
        Check that data is being updated regularly
        """
        logger.info("Checking data freshness...")
        
        with next(get_db()) as session:
            # Check when last score was added
            last_score = session.query(func.max(RawScore.scraped_at)).scalar()
            
            # Check when last model was seen
            last_model_update = session.query(func.max(MasterModel.last_seen)).scalar()
            
            now = datetime.utcnow()
            
            # Check if data is stale
            score_age_hours = (now - last_score).total_seconds() / 3600 if last_score else 999
            model_age_hours = (now - last_model_update).total_seconds() / 3600 if last_model_update else 999
            
            max_age = self.thresholds["max_source_downtime_hours"]
            
            scores_fresh = score_age_hours <= max_age
            models_fresh = model_age_hours <= max_age
            
            self._add_test_result(
                "score_freshness",
                scores_fresh,
                max_age,
                score_age_hours,
                f"Last score: {score_age_hours:.1f}h ago"
            )
            
            self._add_test_result(
                "model_freshness",
                models_fresh,
                max_age,
                model_age_hours,
                f"Last model update: {model_age_hours:.1f}h ago"
            )
            
            if not scores_fresh:
                self._add_alert(
                    AlertLevel.ERROR,
                    "Stale Score Data",
                    f"Last score ingested {score_age_hours:.1f}h ago (threshold: {max_age}h)",
                    "freshness_monitor"
                )
            
            return scores_fresh and models_fresh
    
    async def _check_normalization_quality(self) -> bool:
        """
        Check quality of score normalization
        """
        logger.info("Checking normalization quality...")
        
        with next(get_db()) as session:
            # Check for NaN normalized scores
            total_normalized = session.query(func.count(NormalizedScore.id)).scalar()
            
            if total_normalized == 0:
                self._add_alert(
                    AlertLevel.CRITICAL,
                    "No Normalized Scores",
                    "No normalized scores found in database",
                    "normalization_monitor"
                )
                return False
            
            # Count NaN or invalid scores (this would need proper NULL checking)
            # For SQLite, we check for very high/low values that might indicate errors
            invalid_scores = session.query(func.count(NormalizedScore.id)).filter(
                or_(
                    NormalizedScore.normalized_value > 1000,
                    NormalizedScore.normalized_value < -1000
                )
            ).scalar()
            
            nan_rate = invalid_scores / total_normalized
            
            # Check average confidence
            avg_confidence = session.query(func.avg(NormalizedScore.confidence_score)).scalar()
            
            nan_passed = nan_rate <= self.thresholds["max_nan_scores"]
            confidence_passed = avg_confidence >= self.thresholds["min_confidence_score"]
            
            self._add_test_result(
                "normalization_nan_rate",
                nan_passed,
                self.thresholds["max_nan_scores"],
                nan_rate,
                f"Invalid score rate: {nan_rate:.2%}"
            )
            
            self._add_test_result(
                "normalization_confidence",
                confidence_passed,
                self.thresholds["min_confidence_score"],
                avg_confidence,
                f"Average confidence: {avg_confidence:.3f}"
            )
            
            return nan_passed and confidence_passed
    
    async def _check_model_registry_integrity(self) -> bool:
        """
        Check integrity of model registry
        """
        logger.info("Checking model registry integrity...")
        
        with next(get_db()) as session:
            model_registry = ModelRegistry(session)
            
            # Check for duplicate canonical IDs (shouldn't happen)
            duplicate_query = session.query(
                MasterModel.model_id,
                func.count(MasterModel.model_id)
            ).group_by(MasterModel.model_id).having(func.count(MasterModel.model_id) > 1)
            
            duplicates = duplicate_query.all()
            
            # Check for orphaned aliases
            # (aliases pointing to non-existent models)
            orphaned_aliases = session.query(
                "SELECT COUNT(*) FROM model_aliases a LEFT JOIN master_models m ON a.model_id = m.model_id WHERE m.model_id IS NULL"
            ).scalar()
            
            duplicates_passed = len(duplicates) == 0
            aliases_passed = orphaned_aliases == 0
            
            self._add_test_result(
                "model_registry_duplicates",
                duplicates_passed,
                0,
                len(duplicates),
                f"Found {len(duplicates)} duplicate model IDs"
            )
            
            self._add_test_result(
                "model_registry_orphans",
                aliases_passed,
                0,
                orphaned_aliases,
                f"Found {orphaned_aliases} orphaned aliases"
            )
            
            return duplicates_passed and aliases_passed
    
    async def _check_benchmark_coverage(self) -> bool:
        """
        Check that all benchmark categories have coverage
        """
        logger.info("Checking benchmark category coverage...")
        
        with next(get_db()) as session:
            benchmark_registry = BenchmarkRegistry(session)
            coverage = benchmark_registry.validate_category_coverage()
            
            missing_categories = [
                cat for cat, info in coverage.items()
                if not info["has_coverage"]
            ]
            
            passed = len(missing_categories) == 0
            
            self._add_test_result(
                "benchmark_category_coverage",
                passed,
                100,  # Expect 100% coverage
                ((len(coverage) - len(missing_categories)) / len(coverage)) * 100,
                f"Missing categories: {missing_categories}" if missing_categories else "All categories covered"
            )
            
            if not passed:
                self._add_alert(
                    AlertLevel.WARNING,
                    "Missing Benchmark Categories",
                    f"Categories without benchmarks: {missing_categories}",
                    "benchmark_monitor"
                )
            
            return passed
    
    async def _check_duplicate_detection(self) -> bool:
        """
        Check effectiveness of duplicate detection
        """
        logger.info("Checking duplicate detection...")
        
        with next(get_db()) as session:
            # Look for potential duplicates that weren't caught
            # (models with very similar names)
            models = session.query(MasterModel.model_id, MasterModel.display_name).all()
            
            potential_duplicates = []
            checked = set()
            
            for i, model1 in enumerate(models):
                if model1.model_id in checked:
                    continue
                    
                for model2 in models[i+1:]:
                    if model2.model_id in checked:
                        continue
                    
                    # Simple similarity check
                    similarity = self._calculate_similarity(model1.display_name, model2.display_name)
                    if similarity > 0.8:  # 80% similar
                        potential_duplicates.append((model1.model_id, model2.model_id, similarity))
                
                checked.add(model1.model_id)
            
            passed = len(potential_duplicates) < 10  # Allow some false positives
            
            self._add_test_result(
                "duplicate_detection",
                passed,
                10,
                len(potential_duplicates),
                f"Found {len(potential_duplicates)} potential duplicates"
            )
            
            return passed
    
    async def _check_score_distribution(self) -> bool:
        """
        Check that score distributions look reasonable
        """
        logger.info("Checking score distributions...")
        
        with next(get_db()) as session:
            # Check for reasonable score distributions
            score_stats = session.query(
                func.min(RawScore.value),
                func.max(RawScore.value),
                func.avg(RawScore.value),
                func.count(RawScore.id)
            ).first()
            
            min_score, max_score, avg_score, total_scores = score_stats
            
            # Basic sanity checks
            reasonable_range = (max_score - min_score) < 10000  # Not too wide
            reasonable_average = 0 <= avg_score <= 100  # Most benchmarks are 0-100
            sufficient_data = total_scores > 1000  # Have enough data
            
            passed = reasonable_range and reasonable_average and sufficient_data
            
            self._add_test_result(
                "score_distribution",
                passed,
                1.0,
                1.0 if passed else 0.0,
                f"Range: {min_score:.2f}-{max_score:.2f}, Avg: {avg_score:.2f}, Count: {total_scores}"
            )
            
            return passed
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings (simple implementation)
        """
        if not str1 or not str2:
            return 0.0
        
        # Simple character-based similarity
        str1_lower = str1.lower()
        str2_lower = str2.lower()
        
        if str1_lower == str2_lower:
            return 1.0
        
        # Calculate character overlap
        common_chars = set(str1_lower) & set(str2_lower)
        total_chars = set(str1_lower) | set(str2_lower)
        
        return len(common_chars) / len(total_chars) if total_chars else 0.0
    
    def _add_alert(self, level: AlertLevel, title: str, description: str, source: str, data: Dict = None):
        """
        Add an alert to the system
        """
        alert = QualityAlert(
            level=level,
            title=title,
            description=description,
            timestamp=datetime.utcnow(),
            source=source,
            data=data
        )
        
        self.alerts.append(alert)
        
        # Log the alert
        log_func = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }[level]
        
        log_func(f"[{source}] {title}: {description}")
    
    def _add_test_result(self, test_name: str, passed: bool, threshold: float, actual: float, message: str):
        """
        Add a test result
        """
        result = AcceptanceTestResult(
            test_name=test_name,
            passed=passed,
            threshold=threshold,
            actual_value=actual,
            message=message,
            timestamp=datetime.utcnow()
        )
        
        self.test_results.append(result)
    
    async def _send_alerts(self):
        """
        Send alerts via email/Slack (implementation depends on configuration)
        """
        # For now, just log that alerts would be sent
        critical_alerts = [a for a in self.alerts if a.level == AlertLevel.CRITICAL]
        error_alerts = [a for a in self.alerts if a.level == AlertLevel.ERROR]
        
        if critical_alerts:
            logger.critical(f"CRITICAL ALERTS: {len(critical_alerts)} issues require immediate attention")
        
        if error_alerts:
            logger.error(f"ERROR ALERTS: {len(error_alerts)} issues detected")
        
        # In a real implementation, this would send emails/Slack messages
    
    def _alert_to_dict(self, alert: QualityAlert) -> Dict:
        """
        Convert alert to dictionary for JSON serialization
        """
        return {
            "level": alert.level.value,
            "title": alert.title,
            "description": alert.description,
            "timestamp": alert.timestamp.isoformat(),
            "source": alert.source,
            "data": alert.data
        }
    
    def _test_result_to_dict(self, result: AcceptanceTestResult) -> Dict:
        """
        Convert test result to dictionary for JSON serialization
        """
        return {
            "test_name": result.test_name,
            "passed": result.passed,
            "threshold": result.threshold,
            "actual_value": result.actual_value,
            "message": result.message,
            "timestamp": result.timestamp.isoformat()
        }
    
    def get_quality_dashboard(self) -> Dict:
        """
        Get data for quality monitoring dashboard
        """
        recent_alerts = self.alerts[-50:]  # Last 50 alerts
        recent_tests = self.test_results[-100:]  # Last 100 tests
        
        # Calculate summary statistics
        total_tests = len(recent_tests)
        passed_tests = sum(1 for t in recent_tests if t.passed)
        
        alert_counts = {}
        for level in AlertLevel:
            alert_counts[level.value] = sum(1 for a in recent_alerts if a.level == level)
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "alert_counts": alert_counts
            },
            "recent_alerts": [self._alert_to_dict(a) for a in recent_alerts],
            "recent_tests": [self._test_result_to_dict(t) for t in recent_tests],
            "thresholds": self.thresholds
        }

# Global quality monitor instance
quality_monitor = QualityMonitor()