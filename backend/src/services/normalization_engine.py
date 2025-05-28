"""
Universal Normalization Engine - Task 5.1
Converts all benchmark scores to unified 0-100 scale with confidence scoring

This implements the advanced normalization framework designed by the Planner,
supporting ELO scores, percentages, academic scores, and professional domain metrics.
"""

import re
import math
import logging
from typing import Dict, List, Tuple, Optional, NamedTuple
from enum import Enum
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)

class ScoreType(Enum):
    """Detected score type for appropriate normalization"""
    ELO_RATING = "elo_rating"
    PERCENTAGE = "percentage" 
    DECIMAL_0_1 = "decimal_0_1"
    ACADEMIC_SCORE = "academic_score"
    COST_METRIC = "cost_metric"
    TIME_METRIC = "time_metric"
    TOKEN_COUNT = "token_count"
    UNKNOWN = "unknown"

@dataclass
class NormalizedResult:
    """Result of score normalization with confidence metrics"""
    normalized_value: float      # 0-100 normalized score
    confidence_score: float      # 0-1 confidence in normalization
    normalization_method: str    # Algorithm used
    score_type: ScoreType        # Detected score type
    raw_value: float            # Original value for reference

class ScoreTypeDetector:
    """AI-powered score type detection with confidence scoring"""
    
    def __init__(self):
        # Pattern-based detection rules
        self.elo_patterns = [
            r'elo', r'rating', r'arena', r'rank'
        ]
        self.percentage_patterns = [
            r'accuracy', r'pass', r'rate', r'percent'
        ]
        self.cost_patterns = [
            r'cost', r'price', r'dollar', r'\$'
        ]
        self.time_patterns = [
            r'time', r'latency', r'seconds', r'speed'
        ]
        self.token_patterns = [
            r'token', r'length', r'count'
        ]
    
    def detect_score_type(self, value: float, metric: str, benchmark: str, 
                         leaderboard_name: str) -> Tuple[ScoreType, float]:
        """
        Detect score type with confidence scoring
        
        Returns:
            (ScoreType, confidence_score)
        """
        metric_lower = metric.lower()
        benchmark_lower = benchmark.lower()
        leaderboard_lower = leaderboard_name.lower()
        
        combined_text = f"{metric_lower} {benchmark_lower} {leaderboard_lower}"
        
        # ELO Detection (high confidence if value in expected range)
        if (any(re.search(pattern, combined_text) for pattern in self.elo_patterns) or
            'arena' in combined_text):
            if 800 <= value <= 1600:
                return ScoreType.ELO_RATING, 0.95
            else:
                return ScoreType.ELO_RATING, 0.7
        
        # Cost Detection
        if any(re.search(pattern, combined_text) for pattern in self.cost_patterns):
            return ScoreType.COST_METRIC, 0.9
        
        # Time Detection  
        if any(re.search(pattern, combined_text) for pattern in self.time_patterns):
            return ScoreType.TIME_METRIC, 0.9
            
        # Token Detection
        if any(re.search(pattern, combined_text) for pattern in self.token_patterns):
            return ScoreType.TOKEN_COUNT, 0.85
        
        # Percentage Detection (0-100 range)
        if any(re.search(pattern, combined_text) for pattern in self.percentage_patterns):
            if 0 <= value <= 100:
                return ScoreType.PERCENTAGE, 0.95
            else:
                return ScoreType.PERCENTAGE, 0.7
        
        # Academic Score Detection (0.0-1.0 range)
        if 0 <= value <= 1.0:
            if 'helm' in leaderboard_lower or 'academic' in combined_text:
                return ScoreType.ACADEMIC_SCORE, 0.9
            return ScoreType.DECIMAL_0_1, 0.8
        
        # Default percentage if in 0-100 range
        if 0 <= value <= 100:
            return ScoreType.PERCENTAGE, 0.6
        
        return ScoreType.UNKNOWN, 0.3

class NormalizationAlgorithms:
    """Domain-specific normalization algorithms"""
    
    def normalize_elo_score(self, value: float, domain: str = "general") -> NormalizedResult:
        """
        ELO: 1100-1450 → 0-100 with domain-specific adjustments
        """
        domain_ranges = {
            "math": (1200, 1450),      # Arena Math has higher baseline
            "general": (1100, 1450),    # General Arena scores
            "coding": (1150, 1400),     # Coding-specific ELO
            "conversation": (1100, 1450) # Standard conversation
        }
        
        min_elo, max_elo = domain_ranges.get(domain, (1100, 1450))
        
        # Normalize to 0-100
        normalized = ((value - min_elo) / (max_elo - min_elo)) * 100
        
        # Clamp to valid range
        normalized = max(0, min(100, normalized))
        
        # Confidence based on how well value fits expected range
        if min_elo <= value <= max_elo:
            confidence = 0.95
        elif min_elo - 100 <= value <= max_elo + 100:
            confidence = 0.8
        else:
            confidence = 0.6
        
        return NormalizedResult(
            normalized_value=normalized,
            confidence_score=confidence,
            normalization_method=f"elo_normalization_{domain}",
            score_type=ScoreType.ELO_RATING,
            raw_value=value
        )
    
    def normalize_percentage(self, value: float, benchmark: str) -> NormalizedResult:
        """
        Percentage: Handle 0-100% formats with domain adjustments
        """
        # Direct percentage - already in target range
        normalized = max(0, min(100, value))
        
        # High confidence for values clearly in percentage range
        if 0 <= value <= 100:
            confidence = 0.95
        else:
            confidence = 0.7
        
        return NormalizedResult(
            normalized_value=normalized,
            confidence_score=confidence,
            normalization_method="percentage_direct",
            score_type=ScoreType.PERCENTAGE,
            raw_value=value
        )
    
    def normalize_academic_score(self, value: float, metric: str) -> NormalizedResult:
        """
        HELM Academic: 0.0-1.0 → 0-100 with statistical adjustments
        """
        # Convert decimal to percentage
        normalized = value * 100
        
        # Clamp to valid range
        normalized = max(0, min(100, normalized))
        
        # High confidence for values in expected 0-1 range
        if 0 <= value <= 1.0:
            confidence = 0.95
        else:
            confidence = 0.6
        
        return NormalizedResult(
            normalized_value=normalized,
            confidence_score=confidence,
            normalization_method="academic_decimal_to_percentage",
            score_type=ScoreType.ACADEMIC_SCORE,
            raw_value=value
        )
    
    def normalize_cost_metric(self, value: float) -> NormalizedResult:
        """
        Cost: Logarithmic normalization for efficiency metrics (lower is better)
        """
        # Use logarithmic scale for cost (lower cost = higher score)
        if value <= 0:
            normalized = 100  # Free is perfect
        else:
            # Cap at $1.00, logarithmic scaling
            max_cost = 1.0
            if value >= max_cost:
                normalized = 0
            else:
                # Logarithmic scale: log(max_cost/value) / log(max_cost/min_cost)
                min_cost = 0.001  # $0.001 minimum
                log_ratio = math.log(max_cost / max(value, min_cost)) / math.log(max_cost / min_cost)
                normalized = log_ratio * 100
        
        normalized = max(0, min(100, normalized))
        
        return NormalizedResult(
            normalized_value=normalized,
            confidence_score=0.85,
            normalization_method="cost_logarithmic_inverse",
            score_type=ScoreType.COST_METRIC,
            raw_value=value
        )
    
    def normalize_time_metric(self, value: float) -> NormalizedResult:
        """
        Time: Inverse normalization for latency metrics (lower is better)
        """
        # Cap at 60 seconds, inverse scaling
        max_time = 60.0
        if value <= 0.1:
            normalized = 100  # Very fast is perfect
        elif value >= max_time:
            normalized = 0    # Too slow is zero
        else:
            # Inverse relationship: faster = higher score
            normalized = (1 - (value / max_time)) * 100
        
        normalized = max(0, min(100, normalized))
        
        return NormalizedResult(
            normalized_value=normalized,
            confidence_score=0.85,
            normalization_method="time_inverse",
            score_type=ScoreType.TIME_METRIC,
            raw_value=value
        )

class QualityAssessment:
    """Statistical quality assessment for normalization confidence"""
    
    def calculate_confidence(self, score_distribution: List[float], 
                           detection_confidence: float,
                           outlier_factor: float = 1.0) -> float:
        """
        Calculate normalization confidence based on:
        - Detection confidence
        - Statistical distribution quality  
        - Outlier presence
        """
        if not score_distribution:
            return detection_confidence * 0.5
        
        # Statistical quality metrics
        try:
            std_dev = statistics.stdev(score_distribution) if len(score_distribution) > 1 else 0
            mean_val = statistics.mean(score_distribution)
            
            # Lower standard deviation = more consistent data = higher confidence
            consistency_factor = max(0.5, 1.0 - (std_dev / max(mean_val, 1.0)))
            
            # Combine factors
            final_confidence = detection_confidence * consistency_factor * outlier_factor
            
            return max(0.1, min(1.0, final_confidence))
            
        except Exception:
            return detection_confidence * 0.8
    
    def detect_outliers(self, scores: List[float]) -> List[bool]:
        """Statistical outlier detection using IQR method"""
        if len(scores) < 4:
            return [False] * len(scores)
        
        try:
            sorted_scores = sorted(scores)
            q1_idx = len(sorted_scores) // 4
            q3_idx = 3 * len(sorted_scores) // 4
            
            q1 = sorted_scores[q1_idx]
            q3 = sorted_scores[q3_idx]
            iqr = q3 - q1
            
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            return [score < lower_bound or score > upper_bound for score in scores]
            
        except Exception:
            return [False] * len(scores)

class UniversalNormalizationEngine:
    """Main normalization engine coordinating all components"""
    
    def __init__(self):
        self.detector = ScoreTypeDetector()
        self.algorithms = NormalizationAlgorithms()
        self.quality = QualityAssessment()
        
        logger.info("Universal Normalization Engine initialized")
    
    def normalize_score(self, value: float, metric: str, benchmark: str, 
                       leaderboard_name: str, category: str = "") -> NormalizedResult:
        """
        Main normalization function - automatically detects type and applies algorithm
        """
        try:
            # Step 1: Detect score type
            score_type, detection_confidence = self.detector.detect_score_type(
                value, metric, benchmark, leaderboard_name
            )
            
            # Step 2: Apply appropriate normalization algorithm
            if score_type == ScoreType.ELO_RATING:
                # Determine domain for ELO normalization
                domain = self._determine_elo_domain(category, leaderboard_name)
                result = self.algorithms.normalize_elo_score(value, domain)
                
            elif score_type == ScoreType.PERCENTAGE:
                result = self.algorithms.normalize_percentage(value, benchmark)
                
            elif score_type in [ScoreType.ACADEMIC_SCORE, ScoreType.DECIMAL_0_1]:
                result = self.algorithms.normalize_academic_score(value, metric)
                
            elif score_type == ScoreType.COST_METRIC:
                result = self.algorithms.normalize_cost_metric(value)
                
            elif score_type == ScoreType.TIME_METRIC:
                result = self.algorithms.normalize_time_metric(value)
                
            else:
                # Default: treat as percentage if in reasonable range
                if 0 <= value <= 100:
                    result = self.algorithms.normalize_percentage(value, benchmark)
                else:
                    # Unknown score type - minimal normalization
                    result = NormalizedResult(
                        normalized_value=max(0, min(100, value)),
                        confidence_score=0.3,
                        normalization_method="fallback_clamp",
                        score_type=ScoreType.UNKNOWN,
                        raw_value=value
                    )
            
            # Step 3: Adjust confidence based on detection quality
            final_confidence = min(result.confidence_score, detection_confidence)
            result.confidence_score = final_confidence
            
            return result
            
        except Exception as e:
            logger.error(f"Normalization failed for {value}: {e}")
            # Safe fallback
            return NormalizedResult(
                normalized_value=max(0, min(100, value)),
                confidence_score=0.2,
                normalization_method="error_fallback",
                score_type=ScoreType.UNKNOWN,
                raw_value=value
            )
    
    def _determine_elo_domain(self, category: str, leaderboard_name: str) -> str:
        """Determine ELO domain for appropriate scaling"""
        combined = f"{category} {leaderboard_name}".lower()
        
        if 'math' in combined:
            return "math"
        elif 'cod' in combined or 'programming' in combined:
            return "coding"
        else:
            return "general"
    
    def normalize_batch(self, scores_data: List[Dict]) -> List[NormalizedResult]:
        """
        Batch normalize multiple scores with statistical quality assessment
        """
        results = []
        
        for score_info in scores_data:
            try:
                result = self.normalize_score(
                    value=score_info['value'],
                    metric=score_info['metric'],
                    benchmark=score_info['benchmark'],
                    leaderboard_name=score_info['leaderboard_name'],
                    category=score_info.get('category', '')
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"Batch normalization failed for {score_info}: {e}")
                continue
        
        logger.info(f"Batch normalized {len(results)} scores")
        return results 