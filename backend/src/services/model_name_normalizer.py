"""
Model Name Normalizer Service - Phase 2 Automation
Provides fuzzy matching and pattern-based detection for automatic model name normalization
"""

import logging
import sqlite3
import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict
import difflib

logger = logging.getLogger(__name__)

@dataclass
class ModelMatch:
    """Represents a potential model name match"""
    canonical_name: str
    confidence: float
    match_type: str  # 'exact', 'fuzzy', 'pattern', 'manual'
    original_name: str
    reasoning: str

class ModelNameNormalizer:
    """Service for automatic model name normalization using fuzzy matching and patterns"""
    
    def __init__(self, db_path: str = "meta_llm.db"):
        self.db_path = db_path
        self.confidence_threshold = 0.7
        
        # Common model family patterns
        self.family_patterns = {
            'GPT-4': [
                r'gpt[-_]?4(?:\.?\d+)?(?:[-_]?(?:turbo|o|omni|mini))?',
                r'gpt[-_]?4o[-_]?(?:mini)?',
                r'agentless.*gpt[-_]?4',
                r'.*\+.*gpt[-_]?4',
                r'auto.*gpt[-_]?4',
                r'swe[-_]?agent.*gpt[-_]?4'
            ],
            'Claude 3.5 Sonnet': [
                r'claude[-_]?3\.?5[-_]?sonnet',
                r'claude[-_]?sonnet[-_]?3\.?5',
                r'agentless.*claude[-_]?3\.?5',
                r'.*\+.*claude[-_]?3\.?5[-_]?sonnet',
                r'swe[-_]?agent.*claude[-_]?3\.?5',
                r'auto.*claude[-_]?3\.?5[-_]?sonnet'
            ],
            'Claude 3 Opus': [
                r'claude[-_]?3[-_]?opus',
                r'claude[-_]?opus[-_]?3',
                r'.*\+.*claude[-_]?3[-_]?opus'
            ],
            'Claude 3.7 Sonnet': [
                r'claude[-_]?3\.?7[-_]?sonnet',
                r'claude[-_]?sonnet[-_]?3\.?7'
            ],
            'Claude 2': [
                r'claude[-_]?2(?:\.0)?(?![\d\.])',
                r'.*\+.*claude[-_]?2'
            ],
            'Gemini 2.5 Pro': [
                r'gemini[-_]?2\.?5[-_]?pro',
                r'gemini[-_]?pro[-_]?2\.?5'
            ],
            'Gemini 2.5 Flash': [
                r'gemini[-_]?2\.?5[-_]?flash',
                r'gemini[-_]?flash[-_]?2\.?5'
            ],
            'Gemini 2.0 Flash': [
                r'gemini[-_]?2\.?0[-_]?flash',
                r'gemini[-_]?flash[-_]?2\.?0'
            ],
            'Llama 3.1 70B': [
                r'll?ama[-_]?3\.?1[-_]?70b',
                r'meta[-_]?ll?ama[-_]?3\.?1[-_]?70b'
            ],
            'Llama 2 70B': [
                r'll?ama[-_]?2[-_]?70b',
                r'meta[-_]?ll?ama[-_]?2[-_]?70b'
            ],
            'Llama 2 13B': [
                r'll?ama[-_]?2[-_]?13b',
                r'meta[-_]?ll?ama[-_]?2[-_]?13b'
            ],
            'Llama 2 7B': [
                r'll?ama[-_]?2[-_]?7b',
                r'meta[-_]?ll?ama[-_]?2[-_]?7b'
            ],
            'GPT-3.5 Turbo': [
                r'gpt[-_]?3\.?5[-_]?turbo',
                r'chatgpt[-_]?3\.?5'
            ]
        }
        
        # Common prefixes that indicate wrapped/enhanced models
        self.wrapper_patterns = [
            r'^agentless\s*\+?\s*',
            r'^swe[-_]?agent\s*\+?\s*',
            r'^auto(code)?rover\s*\+?\s*',
            r'^rag\s*\+?\s*',
            r'^composio\s*\+?\s*',
            r'^tools?\s*\+?\s*',
            r'^moatless\s*\+?\s*',
            r'^epam\s*ai\s*\+?\s*',
            r'^.*\s*\+\s*'
        ]
        
        logger.info("ModelNameNormalizer initialized")
    
    def normalize_model_name(self, raw_name: str) -> ModelMatch:
        """
        Normalize a model name using multiple strategies
        
        Args:
            raw_name: Raw model name from scraper
            
        Returns:
            ModelMatch with best candidate
        """
        if not raw_name or not raw_name.strip():
            return ModelMatch(
                canonical_name=raw_name,
                confidence=0.0,
                match_type='exact',
                original_name=raw_name,
                reasoning='Empty or invalid name'
            )
        
        # Check for exact alias match first
        exact_match = self._find_exact_alias(raw_name)
        if exact_match:
            return exact_match
        
        # Try pattern matching
        pattern_match = self._find_pattern_match(raw_name)
        if pattern_match and pattern_match.confidence >= self.confidence_threshold:
            return pattern_match
        
        # Try fuzzy matching against existing canonical names
        fuzzy_match = self._find_fuzzy_match(raw_name)
        if fuzzy_match and fuzzy_match.confidence >= self.confidence_threshold:
            return fuzzy_match
        
        # Return as-is with low confidence
        return ModelMatch(
            canonical_name=raw_name,
            confidence=0.1,
            match_type='manual',
            original_name=raw_name,
            reasoning='No automatic match found - requires manual review'
        )
    
    def _find_exact_alias(self, raw_name: str) -> Optional[ModelMatch]:
        """Find exact alias match in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT canonical_name, model_family
                FROM model_aliases 
                WHERE alias_name = ? OR LOWER(alias_name) = LOWER(?)
            """, (raw_name, raw_name))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return ModelMatch(
                    canonical_name=result[0],
                    confidence=1.0,
                    match_type='exact',
                    original_name=raw_name,
                    reasoning=f'Exact alias match found for {result[1]} family'
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Error finding exact alias for '{raw_name}': {e}")
            return None
    
    def _find_pattern_match(self, raw_name: str) -> Optional[ModelMatch]:
        """Find pattern-based match"""
        raw_name_lower = raw_name.lower()
        
        # Remove common wrapper prefixes
        cleaned_name = raw_name_lower
        for pattern in self.wrapper_patterns:
            cleaned_name = re.sub(pattern, '', cleaned_name, flags=re.IGNORECASE).strip()
        
        best_match = None
        best_confidence = 0.0
        
        for canonical_name, patterns in self.family_patterns.items():
            for pattern in patterns:
                if re.search(pattern, cleaned_name, re.IGNORECASE):
                    # Calculate confidence based on pattern specificity
                    confidence = self._calculate_pattern_confidence(pattern, cleaned_name, raw_name)
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = ModelMatch(
                            canonical_name=canonical_name,
                            confidence=confidence,
                            match_type='pattern',
                            original_name=raw_name,
                            reasoning=f'Pattern match: {pattern} -> {canonical_name}'
                        )
        
        return best_match
    
    def _calculate_pattern_confidence(self, pattern: str, cleaned_name: str, original_name: str) -> float:
        """Calculate confidence score for a pattern match"""
        base_confidence = 0.8
        
        # Boost confidence for more specific patterns
        if '\\d' in pattern:  # Contains version numbers
            base_confidence += 0.1
        
        if 'turbo|o|omni|mini|pro|flash|opus|sonnet' in pattern:  # Contains model variants
            base_confidence += 0.1
        
        # Reduce confidence for very short patterns
        if len(pattern.replace(r'[-_]?', '').replace(r'\.?', '')) < 6:
            base_confidence -= 0.2
        
        # Boost confidence if the match is near the start of the name
        match = re.search(pattern, cleaned_name, re.IGNORECASE)
        if match and match.start() == 0:
            base_confidence += 0.05
        
        return min(1.0, max(0.1, base_confidence))
    
    def _find_fuzzy_match(self, raw_name: str) -> Optional[ModelMatch]:
        """Find fuzzy match against existing canonical names"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT canonical_name FROM model_aliases")
            canonical_names = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            # Use difflib for fuzzy matching
            matches = difflib.get_close_matches(
                raw_name.lower(), 
                [name.lower() for name in canonical_names], 
                n=3, 
                cutoff=0.6
            )
            
            if matches:
                # Find the original canonical name (case-sensitive)
                best_match_lower = matches[0]
                canonical_name = next(
                    name for name in canonical_names 
                    if name.lower() == best_match_lower
                )
                
                # Calculate similarity score
                similarity = difflib.SequenceMatcher(
                    None, raw_name.lower(), best_match_lower
                ).ratio()
                
                return ModelMatch(
                    canonical_name=canonical_name,
                    confidence=similarity,
                    match_type='fuzzy',
                    original_name=raw_name,
                    reasoning=f'Fuzzy match with similarity {similarity:.2f}'
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Error fuzzy matching '{raw_name}': {e}")
            return None
    
    def batch_normalize_new_models(self) -> Dict[str, List[ModelMatch]]:
        """
        Find and normalize all new model names in raw_scores that aren't in aliases
        
        Returns:
            Dict categorized by confidence level
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find model names not in aliases
            cursor.execute("""
                SELECT DISTINCT rs.model_name
                FROM raw_scores rs
                LEFT JOIN model_aliases ma ON rs.model_name = ma.alias_name
                WHERE ma.alias_name IS NULL
                ORDER BY rs.model_name
            """)
            
            unmapped_models = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            logger.info(f"Found {len(unmapped_models)} unmapped model names")
            
            # Categorize results by confidence
            results = {
                'high_confidence': [],    # >= 0.9
                'medium_confidence': [],  # 0.7 - 0.89
                'low_confidence': [],     # 0.3 - 0.69
                'manual_review': []       # < 0.3
            }
            
            for model_name in unmapped_models:
                match = self.normalize_model_name(model_name)
                
                if match.confidence >= 0.9:
                    results['high_confidence'].append(match)
                elif match.confidence >= 0.7:
                    results['medium_confidence'].append(match)
                elif match.confidence >= 0.3:
                    results['low_confidence'].append(match)
                else:
                    results['manual_review'].append(match)
            
            return results
            
        except Exception as e:
            logger.error(f"Error batch normalizing models: {e}")
            return {}
    
    def auto_create_high_confidence_aliases(self, min_confidence: float = 0.9) -> int:
        """
        Automatically create aliases for high-confidence matches
        
        Args:
            min_confidence: Minimum confidence to auto-create alias
            
        Returns:
            Number of aliases created
        """
        batch_results = self.batch_normalize_new_models()
        high_confidence_matches = batch_results.get('high_confidence', [])
        
        created_count = 0
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for match in high_confidence_matches:
                if match.confidence >= min_confidence:
                    # Get family and provider from existing canonical entry
                    cursor.execute("""
                        SELECT model_family, provider
                        FROM model_aliases
                        WHERE canonical_name = ?
                        LIMIT 1
                    """, (match.canonical_name,))
                    
                    meta = cursor.fetchone()
                    if meta:
                        family, provider = meta
                        
                        # Insert new alias
                        cursor.execute("""
                            INSERT OR IGNORE INTO model_aliases
                            (canonical_name, alias_name, model_family, provider)
                            VALUES (?, ?, ?, ?)
                        """, (match.canonical_name, match.original_name, family, provider))
                        
                        if cursor.rowcount > 0:
                            created_count += 1
                            logger.info(f"Auto-created alias: {match.original_name} -> {match.canonical_name} ({match.confidence:.2f})")
            
            conn.commit()
            conn.close()
            
            logger.info(f"Auto-created {created_count} high-confidence aliases")
            return created_count
            
        except Exception as e:
            logger.error(f"Error auto-creating aliases: {e}")
            return 0
    
    def get_normalization_report(self) -> Dict:
        """Generate a comprehensive normalization report"""
        try:
            batch_results = self.batch_normalize_new_models()
            
            # Count existing aliases
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM model_aliases")
            total_aliases = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT canonical_name) FROM model_aliases")
            canonical_models = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT model_name) FROM raw_scores")
            total_models = cursor.fetchone()[0]
            
            conn.close()
            
            unmapped_count = sum(len(matches) for matches in batch_results.values())
            coverage_percent = ((total_models - unmapped_count) / total_models * 100) if total_models > 0 else 0
            
            return {
                'timestamp': datetime.now().isoformat(),
                'coverage': {
                    'total_models_in_db': total_models,
                    'mapped_models': total_models - unmapped_count,
                    'unmapped_models': unmapped_count,
                    'coverage_percentage': round(coverage_percent, 1),
                    'canonical_models': canonical_models,
                    'total_aliases': total_aliases
                },
                'unmapped_breakdown': {
                    'high_confidence': len(batch_results.get('high_confidence', [])),
                    'medium_confidence': len(batch_results.get('medium_confidence', [])),
                    'low_confidence': len(batch_results.get('low_confidence', [])),
                    'manual_review': len(batch_results.get('manual_review', []))
                },
                'recommended_actions': {
                    'auto_create_high_confidence': len(batch_results.get('high_confidence', [])),
                    'review_medium_confidence': len(batch_results.get('medium_confidence', [])),
                    'manual_review_needed': len(batch_results.get('low_confidence', [])) + len(batch_results.get('manual_review', []))
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating normalization report: {e}")
            return {'error': str(e)}
    
    def get_suggested_aliases(self, limit: int = 50) -> List[Dict]:
        """Get suggested aliases for manual review"""
        batch_results = self.batch_normalize_new_models()
        
        suggestions = []
        
        # Add medium and high confidence suggestions
        for confidence_level in ['high_confidence', 'medium_confidence']:
            for match in batch_results.get(confidence_level, []):
                suggestions.append({
                    'original_name': match.original_name,
                    'suggested_canonical': match.canonical_name,
                    'confidence': match.confidence,
                    'match_type': match.match_type,
                    'reasoning': match.reasoning
                })
        
        # Sort by confidence descending
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        
        return suggestions[:limit]