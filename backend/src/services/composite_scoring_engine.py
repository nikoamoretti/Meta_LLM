"""
Composite Scoring Engine - Task 5.2
Calculates weighted composite scores across professional domains with confidence propagation

This implements the advanced composite scoring framework designed by the Planner,
building on the universal normalization foundation from Task 5.1.
"""

import logging
import math
import statistics
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class DomainScore:
    """Individual domain score with confidence metrics"""
    domain: str
    normalized_score: float      # 0-100 normalized score
    confidence: float           # 0-1 confidence in normalization
    benchmark_count: int        # Number of benchmarks in this domain
    raw_scores: List[float]     # Individual benchmark scores for validation

@dataclass
class CompositeResult:
    """Composite score calculation result with full breakdown"""
    model_name: str
    profile_name: str
    composite_score: float      # 0-100 weighted composite score
    confidence_score: float     # 0-1 confidence in composite calculation
    domain_coverage: int        # Number of domains with scores (0-6)
    domain_breakdown: Dict[str, DomainScore]  # Individual domain contributions
    missing_domains: List[str]  # Domains without scores
    calculation_method: str     # Algorithm used
    
class CompositeScoringEngine:
    """Advanced composite scoring with statistical validation and transparency"""
    
    def __init__(self):
        # Domain mapping for weight lookup
        self.domain_weights_map = {
            'academic': 'academic_weight',
            'comprehensive': 'comprehensive_weight', 
            'legal': 'legal_weight',
            'medical': 'medical_weight',
            'reasoning': 'reasoning_weight',
            'software_engineering': 'software_engineering_weight'
        }
        
        logger.info("Composite Scoring Engine initialized")
    
    def calculate_domain_score(self, model_scores: List[Tuple[float, float]]) -> DomainScore:
        """
        Calculate aggregated domain score from multiple benchmarks
        
        Args:
            model_scores: List of (normalized_score, confidence) tuples
            
        Returns:
            DomainScore with aggregated metrics
        """
        if not model_scores:
            return None
            
        scores = [score for score, conf in model_scores]
        confidences = [conf for score, conf in model_scores]
        
        # Confidence-weighted average for domain score
        total_weight = sum(confidences)
        if total_weight == 0:
            # Fallback to simple average if no confidence data
            domain_score = statistics.mean(scores)
            domain_confidence = 0.5
        else:
            weighted_sum = sum(score * conf for score, conf in model_scores)
            domain_score = weighted_sum / total_weight
            domain_confidence = statistics.mean(confidences)
        
        return DomainScore(
            domain="",  # Will be set by caller
            normalized_score=domain_score,
            confidence=domain_confidence,
            benchmark_count=len(model_scores),
            raw_scores=scores
        )
    
    def validate_composite_score(self, domain_scores: Dict[str, DomainScore], 
                                weights: Dict[str, float]) -> Tuple[bool, str]:
        """
        Validate composite score calculation for statistical validity
        
        Returns:
            (is_valid, validation_message)
        """
        if not domain_scores:
            return False, "No domain scores available"
        
        # Check minimum domain coverage
        if len(domain_scores) < 2:
            return False, f"Insufficient domain coverage: {len(domain_scores)}/6 domains"
        
        # Check for reasonable score distribution
        scores = [ds.normalized_score for ds in domain_scores.values()]
        score_std = statistics.stdev(scores) if len(scores) > 1 else 0
        
        # Flag if scores are too uniform (potential data quality issue)
        if score_std < 2.0 and len(scores) > 2:
            return False, f"Suspiciously uniform scores (std={score_std:.2f})"
        
        # Check confidence levels
        avg_confidence = statistics.mean([ds.confidence for ds in domain_scores.values()])
        if avg_confidence < 0.3:
            return False, f"Low confidence scores (avg={avg_confidence:.2f})"
        
        return True, "Validation passed"
    
    def calculate_composite_score(self, model_name: str, domain_scores: Dict[str, DomainScore],
                                profile_weights: Dict[str, float], profile_name: str) -> CompositeResult:
        """
        Calculate weighted composite score with confidence propagation
        
        Args:
            model_name: Name of the model
            domain_scores: Dictionary of domain -> DomainScore
            profile_weights: Dictionary of domain -> weight
            profile_name: Name of the scoring profile
            
        Returns:
            CompositeResult with full calculation breakdown
        """
        try:
            # Validate inputs
            is_valid, validation_msg = self.validate_composite_score(domain_scores, profile_weights)
            if not is_valid:
                logger.warning(f"Composite score validation failed for {model_name}: {validation_msg}")
            
            # Calculate weighted composite score
            weighted_sum = 0.0
            total_weight = 0.0
            confidence_weighted_sum = 0.0
            confidence_total_weight = 0.0
            
            # Track which domains are missing
            available_domains = set(domain_scores.keys())
            all_domains = set(profile_weights.keys())
            missing_domains = list(all_domains - available_domains)
            
            # Calculate with weight redistribution for missing domains
            available_weight_sum = sum(profile_weights[domain] for domain in available_domains)
            
            if available_weight_sum == 0:
                # No domains available - return minimal score
                return CompositeResult(
                    model_name=model_name,
                    profile_name=profile_name,
                    composite_score=0.0,
                    confidence_score=0.0,
                    domain_coverage=0,
                    domain_breakdown={},
                    missing_domains=list(all_domains),
                    calculation_method="no_data_available"
                )
            
            # Redistribute weights proportionally
            weight_multiplier = 1.0 / available_weight_sum
            
            for domain, domain_score in domain_scores.items():
                if domain in profile_weights:
                    # Redistributed weight
                    adjusted_weight = profile_weights[domain] * weight_multiplier
                    
                    # Add to weighted sum
                    weighted_sum += domain_score.normalized_score * adjusted_weight
                    total_weight += adjusted_weight
                    
                    # Confidence-weighted contribution
                    confidence_weighted_sum += domain_score.confidence * adjusted_weight
                    confidence_total_weight += adjusted_weight
            
            # Final composite score
            composite_score = weighted_sum / total_weight if total_weight > 0 else 0.0
            
            # Overall confidence (weighted by domain importance)
            overall_confidence = confidence_weighted_sum / confidence_total_weight if confidence_total_weight > 0 else 0.0
            
            # Adjust confidence based on domain coverage
            coverage_penalty = len(available_domains) / len(all_domains)
            adjusted_confidence = overall_confidence * coverage_penalty
            
            # Determine calculation method
            if len(missing_domains) == 0:
                method = "full_domain_coverage"
            elif len(available_domains) >= 4:
                method = "weight_redistribution_high_coverage"
            elif len(available_domains) >= 2:
                method = "weight_redistribution_moderate_coverage"
            else:
                method = "weight_redistribution_low_coverage"
            
            return CompositeResult(
                model_name=model_name,
                profile_name=profile_name,
                composite_score=round(composite_score, 2),
                confidence_score=round(adjusted_confidence, 3),
                domain_coverage=len(available_domains),
                domain_breakdown=domain_scores.copy(),
                missing_domains=missing_domains,
                calculation_method=method
            )
            
        except Exception as e:
            logger.error(f"Composite score calculation failed for {model_name}: {e}")
            
            # Return error result
            return CompositeResult(
                model_name=model_name,
                profile_name=profile_name,
                composite_score=0.0,
                confidence_score=0.0,
                domain_coverage=0,
                domain_breakdown={},
                missing_domains=list(profile_weights.keys()),
                calculation_method="calculation_error"
            )
    
    def batch_calculate_composite_scores(self, models_data: List[Dict], 
                                       profile_weights: Dict[str, float],
                                       profile_name: str) -> List[CompositeResult]:
        """
        Calculate composite scores for multiple models in batch
        
        Args:
            models_data: List of model data dictionaries
            profile_weights: Scoring profile weights
            profile_name: Name of the scoring profile
            
        Returns:
            List of CompositeResult objects
        """
        results = []
        
        for model_data in models_data:
            try:
                model_name = model_data['model_name']
                domain_scores = model_data['domain_scores']
                
                result = self.calculate_composite_score(
                    model_name=model_name,
                    domain_scores=domain_scores,
                    profile_weights=profile_weights,
                    profile_name=profile_name
                )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Batch calculation failed for model {model_data.get('model_name', 'unknown')}: {e}")
                continue
        
        logger.info(f"Batch calculated composite scores for {len(results)} models using {profile_name} profile")
        return results
    
    def analyze_score_distribution(self, composite_results: List[CompositeResult]) -> Dict:
        """
        Analyze the distribution of composite scores for quality validation
        """
        if not composite_results:
            return {}
        
        scores = [r.composite_score for r in composite_results if r.composite_score > 0]
        confidences = [r.confidence_score for r in composite_results if r.confidence_score > 0]
        coverages = [r.domain_coverage for r in composite_results]
        
        analysis = {
            "total_models": len(composite_results),
            "valid_scores": len(scores),
            "score_statistics": {
                "mean": statistics.mean(scores) if scores else 0,
                "median": statistics.median(scores) if scores else 0,
                "std_dev": statistics.stdev(scores) if len(scores) > 1 else 0,
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0
            },
            "confidence_statistics": {
                "mean": statistics.mean(confidences) if confidences else 0,
                "median": statistics.median(confidences) if confidences else 0,
                "min": min(confidences) if confidences else 0,
                "max": max(confidences) if confidences else 0
            },
            "coverage_statistics": {
                "mean": statistics.mean(coverages) if coverages else 0,
                "full_coverage_count": len([c for c in coverages if c == 6]),
                "high_coverage_count": len([c for c in coverages if c >= 4]),
                "low_coverage_count": len([c for c in coverages if c < 2])
            }
        }
        
        return analysis 