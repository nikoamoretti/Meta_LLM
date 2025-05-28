"""
Composite Scoring Service - Task 5.2
Handles database operations and orchestrates composite score calculation

This service coordinates between the composite scoring engine, normalization data,
and database storage for the unified scoring system.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import sqlite3

from .composite_scoring_engine import CompositeScoringEngine, DomainScore, CompositeResult

logger = logging.getLogger(__name__)

class CompositeScoringService:
    """Service for managing composite scoring operations"""
    
    def __init__(self, db_path: str = "meta_llm.db"):
        self.db_path = db_path
        self.engine = CompositeScoringEngine()
        logger.info("Composite Scoring Service initialized")
    
    def get_scoring_profiles(self) -> List[Dict]:
        """Get all available scoring profiles from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, description, academic_weight, comprehensive_weight,
                       legal_weight, medical_weight, reasoning_weight, software_engineering_weight
                FROM scoring_profiles 
                ORDER BY name
            """)
            
            profiles = []
            for row in cursor.fetchall():
                profiles.append({
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'weights': {
                        'academic': row['academic_weight'],
                        'comprehensive': row['comprehensive_weight'],
                        'legal': row['legal_weight'],
                        'medical': row['medical_weight'],
                        'reasoning': row['reasoning_weight'],
                        'software_engineering': row['software_engineering_weight']
                    }
                })
            
            conn.close()
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to get scoring profiles: {e}")
            return []
    
    def get_model_domain_scores(self) -> Dict[str, Dict[str, DomainScore]]:
        """
        Get normalized scores for all models organized by domain
        
        Returns:
            Dict[model_name -> Dict[domain -> DomainScore]]
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all normalized scores with domain information
            cursor.execute("""
                SELECT 
                    rs.model_name,
                    l.category as domain,
                    ns.normalized_value,
                    ns.confidence_score,
                    rs.benchmark,
                    rs.metric
                FROM raw_scores rs
                JOIN normalized_scores ns ON rs.id = ns.raw_score_id
                JOIN leaderboards l ON rs.leaderboard_id = l.id
                ORDER BY rs.model_name, l.category
            """)
            
            # Group by model and domain
            model_domain_data = defaultdict(lambda: defaultdict(list))
            
            for row in cursor.fetchall():
                model_name = row['model_name']
                domain = row['domain']
                normalized_score = row['normalized_value']
                confidence = row['confidence_score']
                
                model_domain_data[model_name][domain].append((normalized_score, confidence))
            
            conn.close()
            
            # Convert to DomainScore objects
            model_domain_scores = {}
            
            for model_name, domains in model_domain_data.items():
                model_domain_scores[model_name] = {}
                
                for domain, score_data in domains.items():
                    domain_score = self.engine.calculate_domain_score(score_data)
                    if domain_score:
                        domain_score.domain = domain
                        model_domain_scores[model_name][domain] = domain_score
            
            logger.info(f"Retrieved domain scores for {len(model_domain_scores)} models across {len(model_domain_data)} domains")
            return model_domain_scores
            
        except Exception as e:
            logger.error(f"Failed to get model domain scores: {e}")
            return {}
    
    def calculate_all_composite_scores(self, profile_id: int = None) -> Dict[str, List[CompositeResult]]:
        """
        Calculate composite scores for all models using all or specific scoring profile(s)
        
        Args:
            profile_id: Optional specific profile ID, if None calculates for all profiles
            
        Returns:
            Dict[profile_name -> List[CompositeResult]]
        """
        try:
            # Get profiles to process
            profiles = self.get_scoring_profiles()
            if profile_id:
                profiles = [p for p in profiles if p['id'] == profile_id]
            
            if not profiles:
                logger.error("No scoring profiles found")
                return {}
            
            # Get model domain scores
            model_domain_scores = self.get_model_domain_scores()
            if not model_domain_scores:
                logger.error("No model domain scores found")
                return {}
            
            results = {}
            
            for profile in profiles:
                profile_name = profile['name']
                profile_weights = profile['weights']
                
                logger.info(f"Calculating composite scores for profile: {profile_name}")
                
                # Prepare model data for batch calculation
                models_data = []
                for model_name, domain_scores in model_domain_scores.items():
                    models_data.append({
                        'model_name': model_name,
                        'domain_scores': domain_scores
                    })
                
                # Calculate composite scores
                composite_results = self.engine.batch_calculate_composite_scores(
                    models_data=models_data,
                    profile_weights=profile_weights,
                    profile_name=profile_name
                )
                
                # Sort by composite score (descending)
                composite_results.sort(key=lambda x: x.composite_score, reverse=True)
                
                results[profile_name] = composite_results
                
                logger.info(f"Calculated {len(composite_results)} composite scores for {profile_name}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to calculate composite scores: {e}")
            return {}
    
    def save_composite_scores(self, composite_results: Dict[str, List[CompositeResult]]) -> bool:
        """
        Save calculated composite scores to database
        
        Args:
            composite_results: Dict[profile_name -> List[CompositeResult]]
            
        Returns:
            bool: Success status
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get profile name to ID mapping
            cursor.execute("SELECT id, name FROM scoring_profiles")
            profile_mapping = {row[1]: row[0] for row in cursor.fetchall()}
            
            # Clear existing composite scores
            cursor.execute("DELETE FROM composite_scores")
            
            # Insert new composite scores
            for profile_name, results in composite_results.items():
                if profile_name not in profile_mapping:
                    logger.warning(f"Profile {profile_name} not found in database")
                    continue
                
                profile_id = profile_mapping[profile_name]
                
                for result in results:
                    cursor.execute("""
                        INSERT INTO composite_scores 
                        (model_name, profile_id, composite_score, confidence_score, domain_coverage)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        result.model_name,
                        profile_id,
                        result.composite_score,
                        result.confidence_score,
                        result.domain_coverage
                    ))
            
            conn.commit()
            conn.close()
            
            total_scores = sum(len(results) for results in composite_results.values())
            logger.info(f"Saved {total_scores} composite scores to database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save composite scores: {e}")
            return False
    
    def get_composite_leaderboard(self, profile_name: str = "General", limit: int = 50) -> List[Dict]:
        """
        Get composite leaderboard for a specific profile
        
        Args:
            profile_name: Name of scoring profile
            limit: Maximum number of results
            
        Returns:
            List of model dictionaries with composite scores
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    cs.model_name,
                    cs.composite_score,
                    cs.confidence_score,
                    cs.domain_coverage,
                    sp.name as profile_name
                FROM composite_scores cs
                JOIN scoring_profiles sp ON cs.profile_id = sp.id
                WHERE sp.name = ?
                ORDER BY cs.composite_score DESC
                LIMIT ?
            """, (profile_name, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'model_name': row['model_name'],
                    'composite_score': row['composite_score'],
                    'confidence_score': row['confidence_score'],
                    'domain_coverage': row['domain_coverage'],
                    'profile_name': row['profile_name']
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to get composite leaderboard: {e}")
            return []
    
    def get_composite_statistics(self) -> Dict:
        """Get statistical overview of composite scoring system"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Basic statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_composite_scores,
                    COUNT(DISTINCT model_name) as unique_models,
                    COUNT(DISTINCT profile_id) as active_profiles,
                    AVG(composite_score) as avg_composite_score,
                    AVG(confidence_score) as avg_confidence,
                    AVG(domain_coverage) as avg_domain_coverage
                FROM composite_scores
            """)
            
            stats = cursor.fetchone()
            
            # Profile breakdown
            cursor.execute("""
                SELECT 
                    sp.name,
                    COUNT(*) as model_count,
                    AVG(cs.composite_score) as avg_score,
                    AVG(cs.confidence_score) as avg_confidence,
                    MAX(cs.composite_score) as max_score,
                    MIN(cs.composite_score) as min_score
                FROM composite_scores cs
                JOIN scoring_profiles sp ON cs.profile_id = sp.id
                GROUP BY sp.id, sp.name
                ORDER BY sp.name
            """)
            
            profile_stats = []
            for row in cursor.fetchall():
                profile_stats.append({
                    'profile_name': row['name'],
                    'model_count': row['model_count'],
                    'avg_score': round(row['avg_score'], 2) if row['avg_score'] else 0,
                    'avg_confidence': round(row['avg_confidence'], 3) if row['avg_confidence'] else 0,
                    'max_score': row['max_score'],
                    'min_score': row['min_score']
                })
            
            conn.close()
            
            return {
                'overview': {
                    'total_composite_scores': stats['total_composite_scores'],
                    'unique_models': stats['unique_models'],
                    'active_profiles': stats['active_profiles'],
                    'avg_composite_score': round(stats['avg_composite_score'], 2) if stats['avg_composite_score'] else 0,
                    'avg_confidence': round(stats['avg_confidence'], 3) if stats['avg_confidence'] else 0,
                    'avg_domain_coverage': round(stats['avg_domain_coverage'], 1) if stats['avg_domain_coverage'] else 0
                },
                'profiles': profile_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get composite statistics: {e}")
            return {}
    
    def process_all_composite_scores(self) -> Dict:
        """
        Full processing pipeline: calculate and save all composite scores
        
        Returns:
            Processing report with statistics
        """
        try:
            logger.info("Starting full composite score processing pipeline")
            
            # Calculate all composite scores
            composite_results = self.calculate_all_composite_scores()
            
            if not composite_results:
                return {"success": False, "error": "No composite scores calculated"}
            
            # Save to database
            save_success = self.save_composite_scores(composite_results)
            
            if not save_success:
                return {"success": False, "error": "Failed to save composite scores"}
            
            # Get statistics
            statistics = self.get_composite_statistics()
            
            # Analyze score distribution for each profile
            analysis = {}
            for profile_name, results in composite_results.items():
                analysis[profile_name] = self.engine.analyze_score_distribution(results)
            
            report = {
                "success": True,
                "processing_timestamp": datetime.now().isoformat(),
                "statistics": statistics,
                "distribution_analysis": analysis,
                "profiles_processed": list(composite_results.keys()),
                "total_calculations": sum(len(results) for results in composite_results.values())
            }
            
            logger.info(f"Composite score processing completed successfully: {report['total_calculations']} scores calculated")
            return report
            
        except Exception as e:
            logger.error(f"Composite score processing failed: {e}")
            return {"success": False, "error": str(e)} 