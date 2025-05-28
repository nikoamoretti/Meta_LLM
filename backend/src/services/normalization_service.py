"""
Normalization Service - Task 5.1
Handles database operations and batch processing for universal score normalization

This service coordinates between the normalization engine and database,
processing all 1,539 existing scores and handling new scores in real-time.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from .normalization_engine import UniversalNormalizationEngine, NormalizedResult
from ..db.models import RawScore, NormalizedScore, Leaderboard
from ..app.database import SessionLocal

logger = logging.getLogger(__name__)

class ProcessingReport:
    """Report of batch normalization processing"""
    
    def __init__(self):
        self.total_scores = 0
        self.processed_scores = 0
        self.failed_scores = 0
        self.average_confidence = 0.0
        self.processing_time = 0.0
        self.errors = []
        
    def __str__(self):
        return f"""
Normalization Processing Report:
- Total Scores: {self.total_scores}
- Successfully Processed: {self.processed_scores}
- Failed: {self.failed_scores}
- Average Confidence: {self.average_confidence:.3f}
- Processing Time: {self.processing_time:.2f}s
- Success Rate: {(self.processed_scores/self.total_scores)*100:.1f}%
        """

class NormalizationService:
    """Service for managing score normalization and database operations"""
    
    def __init__(self):
        self.engine = UniversalNormalizationEngine()
        logger.info("Normalization Service initialized")
    
    def get_db_session(self) -> Session:
        """Get database session"""
        return SessionLocal()
    
    def normalize_all_scores(self) -> ProcessingReport:
        """
        Batch normalize all existing raw scores in the database
        """
        start_time = datetime.now()
        report = ProcessingReport()
        
        with self.get_db_session() as db:
            try:
                # Get all raw scores with leaderboard info
                query = db.query(
                    RawScore.id,
                    RawScore.value,
                    RawScore.metric,
                    RawScore.benchmark,
                    RawScore.model_name,
                    Leaderboard.name.label('leaderboard_name'),
                    Leaderboard.category
                ).join(Leaderboard).all()
                
                report.total_scores = len(query)
                logger.info(f"Starting batch normalization of {report.total_scores} scores")
                
                # Process in chunks to avoid memory issues
                chunk_size = 100
                processed_count = 0
                
                for i in range(0, len(query), chunk_size):
                    chunk = query[i:i + chunk_size]
                    chunk_results = self._process_score_chunk(db, chunk)
                    
                    processed_count += len(chunk_results)
                    report.processed_scores += len(chunk_results)
                    
                    # Calculate running statistics
                    if chunk_results:
                        chunk_confidence = sum(r.confidence_score for r in chunk_results) / len(chunk_results)
                        logger.info(f"Processed chunk {i//chunk_size + 1}: {len(chunk_results)} scores, avg confidence: {chunk_confidence:.3f}")
                
                # Calculate final statistics
                end_time = datetime.now()
                report.processing_time = (end_time - start_time).total_seconds()
                
                # Get average confidence from database
                avg_confidence = db.query(func.avg(NormalizedScore.confidence_score)).scalar()
                report.average_confidence = avg_confidence or 0.0
                
                report.failed_scores = report.total_scores - report.processed_scores
                
                logger.info(f"Batch normalization complete: {report}")
                return report
                
            except Exception as e:
                logger.error(f"Batch normalization failed: {e}")
                report.errors.append(str(e))
                return report
    
    def _process_score_chunk(self, db: Session, chunk: List) -> List[NormalizedResult]:
        """Process a chunk of raw scores"""
        results = []
        
        for raw_score_data in chunk:
            try:
                # Check if already normalized
                existing = db.query(NormalizedScore).filter(
                    NormalizedScore.raw_score_id == raw_score_data.id
                ).first()
                
                if existing:
                    continue  # Skip already normalized scores
                
                # Normalize the score
                result = self.engine.normalize_score(
                    value=raw_score_data.value,
                    metric=raw_score_data.metric,
                    benchmark=raw_score_data.benchmark,
                    leaderboard_name=raw_score_data.leaderboard_name,
                    category=raw_score_data.category or ""
                )
                
                # Save to database
                normalized_score = NormalizedScore(
                    raw_score_id=raw_score_data.id,
                    normalized_value=result.normalized_value,
                    confidence_score=result.confidence_score,
                    normalization_method=result.normalization_method
                )
                
                db.add(normalized_score)
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Failed to process score ID {raw_score_data.id}: {e}")
                continue
        
        # Commit chunk
        try:
            db.commit()
            logger.debug(f"Committed {len(results)} normalized scores")
        except Exception as e:
            logger.error(f"Failed to commit chunk: {e}")
            db.rollback()
            results = []  # Clear results if commit failed
        
        return results
    
    def normalize_new_score(self, raw_score: RawScore) -> Optional[NormalizedScore]:
        """
        Real-time normalization for new scores
        """
        with self.get_db_session() as db:
            try:
                # Get leaderboard info
                leaderboard = db.query(Leaderboard).filter(
                    Leaderboard.id == raw_score.leaderboard_id
                ).first()
                
                if not leaderboard:
                    logger.error(f"Leaderboard not found for ID {raw_score.leaderboard_id}")
                    return None
                
                # Normalize the score
                result = self.engine.normalize_score(
                    value=raw_score.value,
                    metric=raw_score.metric,
                    benchmark=raw_score.benchmark,
                    leaderboard_name=leaderboard.name,
                    category=leaderboard.category or ""
                )
                
                # Create normalized score record
                normalized_score = NormalizedScore(
                    raw_score_id=raw_score.id,
                    normalized_value=result.normalized_value,
                    confidence_score=result.confidence_score,
                    normalization_method=result.normalization_method
                )
                
                db.add(normalized_score)
                db.commit()
                
                logger.info(f"Normalized new score: {result.normalized_value:.2f} (confidence: {result.confidence_score:.3f})")
                return normalized_score
                
            except Exception as e:
                logger.error(f"Failed to normalize new score: {e}")
                db.rollback()
                return None
    
    def update_normalization_strategy(self, benchmark: str, algorithm: str) -> bool:
        """
        Update normalization strategy for specific benchmark
        (Future enhancement for adaptive algorithms)
        """
        logger.info(f"Normalization strategy update requested for {benchmark}: {algorithm}")
        # Implementation for dynamic algorithm updating
        # This would allow fine-tuning normalization for specific benchmarks
        return True
    
    def get_normalization_statistics(self) -> Dict:
        """Get platform-wide normalization quality metrics"""
        with self.get_db_session() as db:
            try:
                # Basic statistics
                total_normalized = db.query(func.count(NormalizedScore.id)).scalar() or 0
                avg_confidence = db.query(func.avg(NormalizedScore.confidence_score)).scalar() or 0.0
                min_confidence = db.query(func.min(NormalizedScore.confidence_score)).scalar() or 0.0
                max_confidence = db.query(func.max(NormalizedScore.confidence_score)).scalar() or 0.0
                
                # Confidence distribution
                high_confidence = db.query(func.count(NormalizedScore.id)).filter(
                    NormalizedScore.confidence_score >= 0.9
                ).scalar() or 0
                
                medium_confidence = db.query(func.count(NormalizedScore.id)).filter(
                    NormalizedScore.confidence_score >= 0.7,
                    NormalizedScore.confidence_score < 0.9
                ).scalar() or 0
                
                low_confidence = db.query(func.count(NormalizedScore.id)).filter(
                    NormalizedScore.confidence_score < 0.7
                ).scalar() or 0
                
                # Method distribution
                method_stats = db.query(
                    NormalizedScore.normalization_method,
                    func.count(NormalizedScore.id)
                ).group_by(NormalizedScore.normalization_method).all()
                
                return {
                    'total_normalized_scores': total_normalized,
                    'average_confidence': round(avg_confidence, 3),
                    'confidence_range': {
                        'min': round(min_confidence, 3),
                        'max': round(max_confidence, 3)
                    },
                    'confidence_distribution': {
                        'high_confidence_count': high_confidence,
                        'medium_confidence_count': medium_confidence,
                        'low_confidence_count': low_confidence,
                        'high_confidence_percentage': round((high_confidence / total_normalized) * 100, 1) if total_normalized > 0 else 0,
                        'medium_confidence_percentage': round((medium_confidence / total_normalized) * 100, 1) if total_normalized > 0 else 0,
                        'low_confidence_percentage': round((low_confidence / total_normalized) * 100, 1) if total_normalized > 0 else 0
                    },
                    'normalization_methods': {method: count for method, count in method_stats}
                }
                
            except Exception as e:
                logger.error(f"Failed to get normalization statistics: {e}")
                return {'error': str(e)}
    
    def validate_normalization_quality(self) -> Dict:
        """Validate normalization quality across all scores"""
        with self.get_db_session() as db:
            try:
                # Get sample of normalized scores for validation
                sample_scores = db.query(
                    RawScore.value,
                    RawScore.metric,
                    RawScore.benchmark,
                    NormalizedScore.normalized_value,
                    NormalizedScore.confidence_score,
                    NormalizedScore.normalization_method,
                    Leaderboard.name.label('leaderboard_name'),
                    Leaderboard.category
                ).join(NormalizedScore, RawScore.id == NormalizedScore.raw_score_id)\
                 .join(Leaderboard, RawScore.leaderboard_id == Leaderboard.id)\
                 .limit(100).all()
                
                if not sample_scores:
                    return {'error': 'No normalized scores found for validation'}
                
                # Validation checks
                validation_results = {
                    'total_validated': len(sample_scores),
                    'range_violations': 0,
                    'confidence_issues': 0,
                    'suspicious_normalizations': [],
                    'average_confidence': 0.0
                }
                
                confidence_sum = 0
                for score in sample_scores:
                    confidence_sum += score.confidence_score
                    
                    # Check range violations
                    if not (0 <= score.normalized_value <= 100):
                        validation_results['range_violations'] += 1
                    
                    # Check confidence issues
                    if score.confidence_score < 0.5:
                        validation_results['confidence_issues'] += 1
                    
                    # Flag suspicious normalizations
                    if (score.raw_value == score.normalized_value and 
                        score.raw_value > 100):
                        validation_results['suspicious_normalizations'].append({
                            'raw_value': score.raw_value,
                            'normalized_value': score.normalized_value,
                            'metric': score.metric,
                            'leaderboard': score.leaderboard_name
                        })
                
                validation_results['average_confidence'] = confidence_sum / len(sample_scores)
                validation_results['quality_score'] = self._calculate_quality_score(validation_results)
                
                return validation_results
                
            except Exception as e:
                logger.error(f"Validation failed: {e}")
                return {'error': str(e)}
    
    def _calculate_quality_score(self, validation_results: Dict) -> float:
        """Calculate overall quality score for normalization"""
        total = validation_results['total_validated']
        if total == 0:
            return 0.0
        
        # Penalties for issues
        range_penalty = (validation_results['range_violations'] / total) * 0.3
        confidence_penalty = (validation_results['confidence_issues'] / total) * 0.2
        suspicious_penalty = (len(validation_results['suspicious_normalizations']) / total) * 0.2
        
        # Base score from average confidence
        base_score = validation_results['average_confidence']
        
        # Apply penalties
        quality_score = base_score - range_penalty - confidence_penalty - suspicious_penalty
        
        return max(0.0, min(1.0, quality_score)) 