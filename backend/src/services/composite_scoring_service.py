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
    
    def get_canonical_model_name(self, alias_name: str) -> str:
        """
        Resolve an alias model name to its canonical name
        
        Args:
            alias_name: The model name (could be an alias)
            
        Returns:
            Canonical model name, or original name if no mapping exists
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT canonical_name 
                FROM model_aliases 
                WHERE alias = ?
            """, (alias_name,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            else:
                # Return original name if no mapping found
                return alias_name
                
        except Exception as e:
            logger.warning(f"Failed to resolve model alias '{alias_name}': {e}")
            return alias_name
    
    def get_alias_mappings(self) -> Dict[str, str]:
        """
        Get all alias-to-canonical mappings for batch processing
        
        Returns:
            Dict[alias_name -> canonical_name]
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT alias, canonical_name FROM model_aliases")
            mappings = {row[0]: row[1] for row in cursor.fetchall()}
            
            conn.close()
            return mappings
            
        except Exception as e:
            logger.error(f"Failed to get alias mappings: {e}")
            return {}
    
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
        Get normalized scores for all models organized by domain, using canonical model names
        Aggregates scores from all aliases into their canonical form
        
        Returns:
            Dict[canonical_model_name -> Dict[domain -> DomainScore]]
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
            
            # Get alias mappings for batch processing
            alias_mappings = self.get_alias_mappings()
            
            # Group by canonical model name and domain
            canonical_model_domain_data = defaultdict(lambda: defaultdict(list))
            original_models_processed = set()
            
            for row in cursor.fetchall():
                original_model_name = row['model_name']
                domain = row['domain']
                normalized_score = row['normalized_value']
                confidence = row['confidence_score']
                
                # Resolve to canonical name
                canonical_name = alias_mappings.get(original_model_name, original_model_name)
                
                canonical_model_domain_data[canonical_name][domain].append((normalized_score, confidence))
                original_models_processed.add(original_model_name)
            
            conn.close()
            
            # Convert to DomainScore objects
            canonical_model_domain_scores = {}
            
            for canonical_name, domains in canonical_model_domain_data.items():
                canonical_model_domain_scores[canonical_name] = {}
                
                for domain, score_data in domains.items():
                    domain_score = self.engine.calculate_domain_score(score_data)
                    if domain_score:
                        domain_score.domain = domain
                        canonical_model_domain_scores[canonical_name][domain] = domain_score
            
            # Log aggregation results
            aliases_used = len([name for name in original_models_processed if name in alias_mappings])
            canonical_models = len(canonical_model_domain_scores)
            
            logger.info(f"Model name aggregation completed:")
            logger.info(f"  - {len(original_models_processed)} original model names processed")
            logger.info(f"  - {aliases_used} aliases resolved to canonical names")
            logger.info(f"  - {canonical_models} canonical models with domain scores")
            
            return canonical_model_domain_scores
            
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
        Get composite leaderboard for a specific profile with individual domain scores
        
        Args:
            profile_name: Name of scoring profile
            limit: Maximum number of results
            
        Returns:
            List of model dictionaries with composite scores and domain scores
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get composite scores
            cursor.execute("""
                SELECT 
                    cs.model_name,
                    cs.composite_score,
                    cs.confidence_score,
                    cs.domain_coverage,
                    sp.name as profile_name
                FROM composite_scores cs
                JOIN scoring_profiles sp ON cs.profile_id = sp.id
                WHERE LOWER(sp.name) = LOWER(?)
                ORDER BY cs.composite_score DESC
                LIMIT ?
            """, (profile_name, limit))
            
            composite_results = cursor.fetchall()
            
            # Get domain scores for all models in the leaderboard
            model_names = [row['model_name'] for row in composite_results]
            if not model_names:
                conn.close()
                return []
            
            # Create placeholders for the IN clause
            placeholders = ','.join('?' * len(model_names))
            
            # Get individual domain scores - try with aliases first, then without
            domain_scores_by_model = defaultdict(dict)
            
            # First try with model aliases
            cursor.execute(f"""
                SELECT 
                    ma.canonical_name as canonical_model,
                    rs.model_name as raw_model_name,
                    l.category as domain,
                    AVG(ns.normalized_value) as avg_score,
                    AVG(ns.confidence_score) as avg_confidence,
                    COUNT(*) as benchmark_count
                FROM raw_scores rs
                JOIN normalized_scores ns ON rs.id = ns.raw_score_id
                JOIN leaderboards l ON rs.leaderboard_id = l.id
                JOIN model_aliases ma ON rs.model_name = ma.alias
                WHERE ma.canonical_name IN ({placeholders})
                GROUP BY ma.canonical_name, l.category
                ORDER BY ma.canonical_name, l.category
            """, model_names)
            
            # Collect alias-based scores
            for row in cursor.fetchall():
                canonical_model = row['canonical_model']
                domain = row['domain']
                score = row['avg_score'] if row['avg_score'] is not None else None
                domain_scores_by_model[canonical_model][domain] = score
            
            # For models without alias mappings, try direct model name matching
            models_without_scores = [model for model in model_names if not domain_scores_by_model[model]]
            if models_without_scores:
                placeholders_direct = ','.join('?' * len(models_without_scores))
                cursor.execute(f"""
                    SELECT 
                        rs.model_name as canonical_model,
                        l.category as domain,
                        AVG(ns.normalized_value) as avg_score,
                        AVG(ns.confidence_score) as avg_confidence,
                        COUNT(*) as benchmark_count
                    FROM raw_scores rs
                    JOIN normalized_scores ns ON rs.id = ns.raw_score_id
                    JOIN leaderboards l ON rs.leaderboard_id = l.id
                    WHERE rs.model_name IN ({placeholders_direct})
                    GROUP BY rs.model_name, l.category
                    ORDER BY rs.model_name, l.category
                """, models_without_scores)
                
                # Add direct-match scores
                for row in cursor.fetchall():
                    canonical_model = row['canonical_model']
                    domain = row['domain']
                    score = row['avg_score'] if row['avg_score'] is not None else None
                    domain_scores_by_model[canonical_model][domain] = score
            
            
            # Combine composite and domain scores
            results = []
            for row in composite_results:
                model_name = row['model_name']
                model_data = {
                    'model_name': model_name,
                    'composite_score': row['composite_score'],
                    'confidence_score': row['confidence_score'],
                    'domain_coverage': row['domain_coverage'],
                    'profile_name': row['profile_name'],
                    'domain_scores': {
                        'software_engineering': domain_scores_by_model[model_name].get('software_engineering', None),
                        'reasoning': domain_scores_by_model[model_name].get('reasoning', None),
                        'academic': domain_scores_by_model[model_name].get('academic', None),
                        'medical': domain_scores_by_model[model_name].get('medical', None),
                        'legal': domain_scores_by_model[model_name].get('legal', None),
                        'comprehensive': domain_scores_by_model[model_name].get('comprehensive', None),
                        'safety': domain_scores_by_model[model_name].get('safety', None),
                        'finance': domain_scores_by_model[model_name].get('finance', None)
                    }
                }
                results.append(model_data)
            
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
    
    def get_model_individual_benchmarks(self, model_name: str, category: Optional[str] = None) -> List[Dict]:
        """
        Get individual benchmark scores for a specific model
        
        Args:
            model_name: Name of the model to get benchmarks for
            category: Optional category filter (e.g., 'software_engineering')
            
        Returns:
            List of individual benchmark scores
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query with optional category filter
            query = """
                SELECT 
                    rs.benchmark,
                    rs.score as raw_score,
                    ns.normalized_value as normalized_score,
                    ns.confidence_score,
                    l.category,
                    l.source,
                    l.name as leaderboard_name
                FROM raw_scores rs
                JOIN normalized_scores ns ON rs.id = ns.raw_score_id
                JOIN leaderboards l ON rs.leaderboard_id = l.id
                WHERE rs.model_name = ?
            """
            params = [model_name]
            
            if category:
                query += " AND l.category = ?"
                params.append(category)
            
            query += " ORDER BY l.category, rs.benchmark"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            benchmarks = []
            for row in results:
                benchmarks.append({
                    'benchmark': row['benchmark'],
                    'raw_score': row['raw_score'],
                    'normalized_score': row['normalized_score'],
                    'confidence_score': row['confidence_score'],
                    'category': row['category'],
                    'source': row['source'],
                    'leaderboard_name': row['leaderboard_name']
                })
            
            conn.close()
            return benchmarks
            
        except Exception as e:
            logger.error(f"Failed to get individual benchmarks for model {model_name}: {e}")
            return []
    
    def get_category_benchmark_breakdown(self, category_name: str, limit: int = 20) -> Dict:
        """
        Get individual benchmark breakdown for all models in a category
        
        Args:
            category_name: Category to analyze (e.g., 'software_engineering', 'coding')
            limit: Maximum number of models to include
            
        Returns:
            Dictionary with benchmark breakdown data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Map frontend category names to database categories
            category_mapping = {
                'coding': 'software_engineering',
                'research': 'academic',
                'general': 'comprehensive'
            }
            
            db_category = category_mapping.get(category_name, category_name)
            
            # Get all benchmarks in this category
            cursor.execute("""
                SELECT DISTINCT rs.benchmark, l.name as leaderboard_name
                FROM raw_scores rs
                JOIN leaderboards l ON rs.leaderboard_id = l.id
                WHERE l.category = ?
                ORDER BY rs.benchmark
            """, (db_category,))
            
            benchmarks_info = cursor.fetchall()
            benchmarks = [row['benchmark'] for row in benchmarks_info]
            
            # Get top models with scores in this category
            cursor.execute("""
                SELECT 
                    rs.model_name,
                    rs.benchmark,
                    rs.value as raw_score,
                    ns.normalized_value as normalized_score,
                    ns.confidence_score
                FROM raw_scores rs
                JOIN normalized_scores ns ON rs.id = ns.raw_score_id
                JOIN leaderboards l ON rs.leaderboard_id = l.id
                WHERE l.category = ?
                ORDER BY rs.model_name, rs.benchmark
            """, (db_category,))
            
            results = cursor.fetchall()
            
            # Group by model
            models_data = defaultdict(lambda: {'model_name': '', 'benchmarks': {}, 'average_score': 0})
            
            for row in results:
                model_name = row['model_name']
                models_data[model_name]['model_name'] = model_name
                models_data[model_name]['benchmarks'][row['benchmark']] = {
                    'raw_score': row['raw_score'],
                    'normalized_score': row['normalized_score'],
                    'confidence_score': row['confidence_score']
                }
            
            # Calculate average scores and sort
            for model_name, data in models_data.items():
                scores = [b['normalized_score'] for b in data['benchmarks'].values() if b['normalized_score'] is not None]
                data['average_score'] = sum(scores) / len(scores) if scores else 0
            
            # Sort by average score and limit results
            sorted_models = sorted(
                models_data.values(), 
                key=lambda x: x['average_score'], 
                reverse=True
            )[:limit]
            
            conn.close()
            
            return {
                'benchmarks': [
                    {
                        'name': info['benchmark'],
                        'leaderboard': info['leaderboard_name']
                    }
                    for info in benchmarks_info
                ],
                'models': sorted_models
            }
            
        except Exception as e:
            logger.error(f"Failed to get category benchmark breakdown for {category_name}: {e}")
            return {} 