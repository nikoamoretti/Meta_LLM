"""
Automated Normalization Service
Integrates model name normalization into the scraping and scoring pipeline
"""

import logging
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime
from .model_name_normalizer import ModelNameNormalizer, ModelMatch
from .composite_scoring_service import CompositeScoringService

logger = logging.getLogger(__name__)

class AutomatedNormalizationService:
    """Service that automatically normalizes model names during data processing"""
    
    def __init__(self, db_path: str = "meta_llm.db"):
        self.db_path = db_path
        self.normalizer = ModelNameNormalizer(db_path)
        self.composite_service = CompositeScoringService(db_path)
        
        # Configuration
        self.auto_create_threshold = 0.9  # Auto-create aliases above this confidence
        self.batch_size = 100
        
        logger.info("AutomatedNormalizationService initialized")
    
    def process_scraped_models(self, raw_models: List[Dict], source_name: str) -> Dict:
        """
        Process a list of scraped models and normalize their names
        
        Args:
            raw_models: List of model data from scrapers
            source_name: Name of the data source
            
        Returns:
            Processing report with statistics
        """
        logger.info(f"Processing {len(raw_models)} models from {source_name}")
        
        stats = {
            'total_processed': 0,
            'already_mapped': 0,
            'auto_normalized': 0,
            'new_aliases_created': 0,
            'manual_review_needed': 0,
            'errors': 0
        }
        
        models_for_review = []
        
        for model_data in raw_models:
            try:
                model_name = model_data.get('model', '')
                if not model_name:
                    continue
                
                stats['total_processed'] += 1
                
                # Check if already mapped
                if self._is_already_mapped(model_name):
                    stats['already_mapped'] += 1
                    continue
                
                # Normalize the model name
                match = self.normalizer.normalize_model_name(model_name)
                
                if match.confidence >= self.auto_create_threshold:
                    # Auto-create alias
                    if self._create_alias(match):
                        stats['new_aliases_created'] += 1
                        stats['auto_normalized'] += 1
                        logger.info(f"Auto-normalized: {model_name} -> {match.canonical_name} ({match.confidence:.2f})")
                    else:
                        stats['errors'] += 1
                elif match.confidence >= 0.3:
                    # Add to manual review
                    models_for_review.append({
                        'original_name': model_name,
                        'suggested_canonical': match.canonical_name,
                        'confidence': match.confidence,
                        'reasoning': match.reasoning,
                        'source': source_name
                    })
                    stats['manual_review_needed'] += 1
                else:
                    stats['manual_review_needed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing model {model_data.get('model', 'unknown')}: {e}")
                stats['errors'] += 1
        
        # Store models needing review
        if models_for_review:
            self._store_review_queue(models_for_review)
        
        logger.info(f"Model processing completed: {stats}")
        return stats
    
    def _is_already_mapped(self, model_name: str) -> bool:
        """Check if model name is already in aliases table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 1 FROM model_aliases 
                WHERE alias_name = ? OR LOWER(alias_name) = LOWER(?)
                LIMIT 1
            """, (model_name, model_name))
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            logger.warning(f"Error checking if model '{model_name}' is mapped: {e}")
            return False
    
    def _create_alias(self, match: ModelMatch) -> bool:
        """Create a new alias in the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get family and provider from existing canonical entry
            cursor.execute("""
                SELECT model_family, provider
                FROM model_aliases
                WHERE canonical_name = ?
                LIMIT 1
            """, (match.canonical_name,))
            
            meta = cursor.fetchone()
            if not meta:
                logger.warning(f"No metadata found for canonical name: {match.canonical_name}")
                conn.close()
                return False
            
            family, provider = meta
            
            # Insert new alias
            cursor.execute("""
                INSERT OR IGNORE INTO model_aliases
                (canonical_name, alias_name, model_family, provider)
                VALUES (?, ?, ?, ?)
            """, (match.canonical_name, match.original_name, family, provider))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating alias for {match.original_name}: {e}")
            return False
    
    def _store_review_queue(self, models_for_review: List[Dict]):
        """Store models requiring manual review in a queue table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create review queue table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS normalization_review_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_name TEXT NOT NULL,
                    suggested_canonical TEXT,
                    confidence REAL,
                    reasoning TEXT,
                    source TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    reviewed_by TEXT,
                    UNIQUE(original_name)
                )
            """)
            
            # Insert models for review
            for model in models_for_review:
                cursor.execute("""
                    INSERT OR REPLACE INTO normalization_review_queue
                    (original_name, suggested_canonical, confidence, reasoning, source)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    model['original_name'],
                    model['suggested_canonical'],
                    model['confidence'],
                    model['reasoning'],
                    model['source']
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Added {len(models_for_review)} models to review queue")
            
        except Exception as e:
            logger.error(f"Error storing review queue: {e}")
    
    def run_daily_normalization(self) -> Dict:
        """
        Run daily normalization process on all unmapped models
        
        Returns:
            Processing report
        """
        logger.info("Starting daily normalization process")
        
        try:
            # Get normalization report
            report = self.normalizer.get_normalization_report()
            
            # Auto-create high confidence aliases
            created_count = self.normalizer.auto_create_high_confidence_aliases()
            
            # If new aliases were created, recalculate composite scores
            if created_count > 0:
                logger.info("New aliases created, recalculating composite scores...")
                composite_report = self.composite_service.process_all_composite_scores()
                
                report['composite_scores'] = {
                    'recalculated': composite_report.get('success', False),
                    'total_scores': composite_report.get('total_calculations', 0)
                }
            
            report['new_aliases_created'] = created_count
            report['timestamp'] = datetime.now().isoformat()
            
            logger.info(f"Daily normalization completed: {created_count} new aliases created")
            return report
            
        except Exception as e:
            logger.error(f"Daily normalization failed: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def get_review_queue(self, limit: int = 50, status: str = 'pending') -> List[Dict]:
        """Get models in the review queue"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT original_name, suggested_canonical, confidence, reasoning, 
                       source, created_at, status
                FROM normalization_review_queue
                WHERE status = ?
                ORDER BY confidence DESC, created_at DESC
                LIMIT ?
            """, (status, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'original_name': row['original_name'],
                    'suggested_canonical': row['suggested_canonical'],
                    'confidence': row['confidence'],
                    'reasoning': row['reasoning'],
                    'source': row['source'],
                    'created_at': row['created_at'],
                    'status': row['status']
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error getting review queue: {e}")
            return []
    
    def approve_suggestion(self, original_name: str, canonical_name: str, reviewer: str = 'system') -> bool:
        """Approve a normalization suggestion and create the alias"""
        try:
            # Create the alias
            match = ModelMatch(
                canonical_name=canonical_name,
                confidence=1.0,
                match_type='manual',
                original_name=original_name,
                reasoning='Manually approved'
            )
            
            success = self._create_alias(match)
            
            if success:
                # Update review queue
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE normalization_review_queue
                    SET status = 'approved', reviewed_at = ?, reviewed_by = ?
                    WHERE original_name = ?
                """, (datetime.now(), reviewer, original_name))
                
                conn.commit()
                conn.close()
                
                logger.info(f"Approved alias: {original_name} -> {canonical_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error approving suggestion for {original_name}: {e}")
            return False
    
    def reject_suggestion(self, original_name: str, reviewer: str = 'system') -> bool:
        """Reject a normalization suggestion"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE normalization_review_queue
                SET status = 'rejected', reviewed_at = ?, reviewed_by = ?
                WHERE original_name = ?
            """, (datetime.now(), reviewer, original_name))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Rejected suggestion for: {original_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error rejecting suggestion for {original_name}: {e}")
            return False
    
    def get_normalization_statistics(self) -> Dict:
        """Get current normalization statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get basic counts
            cursor.execute("SELECT COUNT(*) FROM model_aliases")
            total_aliases = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT canonical_name) FROM model_aliases")
            canonical_models = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT model_name) FROM raw_scores")
            total_models_in_db = cursor.fetchone()[0]
            
            # Get unmapped count
            cursor.execute("""
                SELECT COUNT(DISTINCT rs.model_name)
                FROM raw_scores rs
                LEFT JOIN model_aliases ma ON rs.model_name = ma.alias_name
                WHERE ma.alias_name IS NULL
            """)
            unmapped_models = cursor.fetchone()[0]
            
            # Get review queue stats
            cursor.execute("SELECT COUNT(*) FROM normalization_review_queue WHERE status = 'pending'")
            pending_review = cursor.fetchone()[0] if cursor.fetchone() else 0
            
            cursor.execute("SELECT COUNT(*) FROM normalization_review_queue WHERE status = 'approved'")
            approved_count = cursor.fetchone()[0] if cursor.fetchone() else 0
            
            conn.close()
            
            coverage_percent = ((total_models_in_db - unmapped_models) / total_models_in_db * 100) if total_models_in_db > 0 else 0
            
            return {
                'total_models_in_db': total_models_in_db,
                'total_aliases': total_aliases,
                'canonical_models': canonical_models,
                'mapped_models': total_models_in_db - unmapped_models,
                'unmapped_models': unmapped_models,
                'coverage_percentage': round(coverage_percent, 1),
                'pending_review': pending_review,
                'approved_suggestions': approved_count,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting normalization statistics: {e}")
            return {'error': str(e)}