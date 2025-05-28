"""
Composite Scoring API v3 - Task 5.2
Enhanced endpoints with composite scoring, professional profiles, and transparency

This implements the API integration layer for Task 5.2 composite scoring framework.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
from datetime import datetime

from ..database import get_db
from ...services.composite_scoring_service import CompositeScoringService
from .models import (
    NormalizedModelScore, DetailedScoreResponse, NormalizationStats, 
    ProcessingReportResponse, CategoryScore
)

router = APIRouter()

# Initialize composite scoring service
composite_service = CompositeScoringService()

@router.get("/composite/leaderboard/{profile_name}")
async def get_composite_leaderboard(
    profile_name: str = "General",
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get composite leaderboard for a specific scoring profile
    
    Available profiles: General, Academic, Developer, Healthcare, Legal
    """
    try:
        leaderboard = composite_service.get_composite_leaderboard(profile_name, limit)
        
        if not leaderboard:
            raise HTTPException(status_code=404, detail=f"No results found for profile: {profile_name}")
        
        return {
            "profile_name": profile_name,
            "total_models": len(leaderboard),
            "generated_at": datetime.now().isoformat(),
            "leaderboard": leaderboard
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get composite leaderboard: {str(e)}")

@router.get("/composite/profiles")
async def get_scoring_profiles():
    """Get all available scoring profiles with their weight configurations"""
    try:
        profiles = composite_service.get_scoring_profiles()
        
        return {
            "total_profiles": len(profiles),
            "profiles": profiles
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scoring profiles: {str(e)}")

@router.get("/composite/model/{model_name}")
async def get_model_composite_details(
    model_name: str,
    profile_name: str = Query("General", description="Scoring profile to use")
):
    """Get detailed composite score breakdown for a specific model"""
    try:
        # Get model's composite score for the profile
        leaderboard = composite_service.get_composite_leaderboard(profile_name, limit=1000)
        model_data = next((m for m in leaderboard if m['model_name'] == model_name), None)
        
        if not model_data:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found in {profile_name} profile")
        
        # Get model's domain scores for breakdown
        domain_scores = composite_service.get_model_domain_scores()
        model_domains = domain_scores.get(model_name, {})
        
        # Get profile weights
        profiles = composite_service.get_scoring_profiles()
        profile = next((p for p in profiles if p['name'] == profile_name), None)
        
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile '{profile_name}' not found")
        
        # Build detailed breakdown
        domain_breakdown = {}
        for domain, domain_score in model_domains.items():
            domain_breakdown[domain] = {
                "domain_score": round(domain_score.normalized_score, 2),
                "confidence": round(domain_score.confidence, 3),
                "benchmark_count": domain_score.benchmark_count,
                "weight_in_profile": profile['weights'].get(domain, 0),
                "contribution": round(domain_score.normalized_score * profile['weights'].get(domain, 0), 2)
            }
        
        # Calculate missing domains
        all_domains = set(profile['weights'].keys())
        present_domains = set(model_domains.keys())
        missing_domains = list(all_domains - present_domains)
        
        return {
            "model_name": model_name,
            "profile_name": profile_name,
            "composite_score": model_data['composite_score'],
            "confidence_score": model_data['confidence_score'],
            "domain_coverage": f"{model_data['domain_coverage']}/6",
            "domain_breakdown": domain_breakdown,
            "missing_domains": missing_domains,
            "profile_weights": profile['weights'],
            "methodology": {
                "calculation_method": "confidence_weighted_average_with_redistribution",
                "weight_redistribution": len(missing_domains) > 0,
                "confidence_adjustment": "coverage_penalty_applied"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model details: {str(e)}")

@router.get("/composite/statistics")
async def get_composite_statistics():
    """Get comprehensive statistics about the composite scoring system"""
    try:
        stats = composite_service.get_composite_statistics()
        
        if not stats:
            raise HTTPException(status_code=404, detail="No composite scoring statistics available")
        
        return {
            "generated_at": datetime.now().isoformat(),
            "system_overview": stats['overview'],
            "profile_statistics": stats['profiles'],
            "methodology": {
                "normalization_source": "Task 5.1 Universal Normalization Framework",
                "score_range": "0-100 normalized scale",
                "weighting_method": "Professional domain-specific weights",
                "confidence_scoring": "Statistical validation with coverage adjustment",
                "transparency": "Full calculation breakdown available per model"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get composite statistics: {str(e)}")

@router.get("/composite/leaderboard/compare")
async def compare_profiles(
    limit: int = Query(20, ge=1, le=100),
    models: Optional[str] = Query(None, description="Comma-separated model names to focus on")
):
    """Compare model rankings across different scoring profiles"""
    try:
        profiles = ["General", "Academic", "Developer", "Healthcare", "Legal"]
        profile_data = {}
        
        # Get leaderboards for each profile
        for profile in profiles:
            leaderboard = composite_service.get_composite_leaderboard(profile, limit)
            profile_data[profile] = {model['model_name']: model for model in leaderboard}
        
        # Filter to specific models if requested
        if models:
            model_list = [m.strip() for m in models.split(',')]
            filtered_data = {}
            for profile, data in profile_data.items():
                filtered_data[profile] = {k: v for k, v in data.items() if k in model_list}
            profile_data = filtered_data
        
        # Find common models across profiles
        all_models = set()
        for data in profile_data.values():
            all_models.update(data.keys())
        
        # Build comparison data
        comparison = []
        for model in sorted(all_models):
            model_comparison = {"model_name": model}
            
            for profile in profiles:
                if model in profile_data[profile]:
                    model_comparison[profile.lower()] = {
                        "score": profile_data[profile][model]['composite_score'],
                        "rank": None  # Could calculate rank if needed
                    }
                else:
                    model_comparison[profile.lower()] = None
            
            comparison.append(model_comparison)
        
        # Sort by General profile score
        comparison.sort(
            key=lambda x: x.get('general', {}).get('score', 0) if x.get('general') else 0, 
            reverse=True
        )
        
        return {
            "total_models": len(comparison),
            "profiles_compared": profiles,
            "comparison": comparison[:limit],
            "note": "Rankings may vary significantly across profiles due to different domain weightings"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare profiles: {str(e)}")

@router.post("/composite/calculate")
async def trigger_composite_calculation():
    """Trigger recalculation of all composite scores (admin endpoint)"""
    try:
        report = composite_service.process_all_composite_scores()
        
        if not report.get("success"):
            raise HTTPException(status_code=500, detail=f"Calculation failed: {report.get('error')}")
        
        return {
            "success": True,
            "message": "Composite scores successfully recalculated",
            "processing_report": report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger calculation: {str(e)}")

@router.get("/composite/domain-coverage")
async def get_domain_coverage_analysis():
    """Analyze domain coverage across all models"""
    try:
        stats = composite_service.get_composite_statistics()
        
        # Get detailed coverage analysis
        model_domain_scores = composite_service.get_model_domain_scores()
        
        coverage_analysis = {
            "total_models": len(model_domain_scores),
            "coverage_distribution": {
                "full_coverage": 0,      # 6/6 domains
                "high_coverage": 0,      # 4-5/6 domains  
                "moderate_coverage": 0,  # 2-3/6 domains
                "low_coverage": 0        # 1/6 domains
            },
            "domain_popularity": {}
        }
        
        # Analyze coverage
        domain_counts = {}
        for model, domains in model_domain_scores.items():
            coverage = len(domains)
            
            if coverage == 6:
                coverage_analysis["coverage_distribution"]["full_coverage"] += 1
            elif coverage >= 4:
                coverage_analysis["coverage_distribution"]["high_coverage"] += 1
            elif coverage >= 2:
                coverage_analysis["coverage_distribution"]["moderate_coverage"] += 1
            else:
                coverage_analysis["coverage_distribution"]["low_coverage"] += 1
            
            # Count domain appearances
            for domain in domains:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        coverage_analysis["domain_popularity"] = domain_counts
        
        return coverage_analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze domain coverage: {str(e)}")

@router.get("/composite/methodology")
async def get_methodology_explanation():
    """Get detailed explanation of the composite scoring methodology"""
    return {
        "composite_scoring_methodology": {
            "overview": "Professional domain-weighted composite scoring with statistical validation",
            "foundation": "Task 5.1 Universal Normalization Framework (0-100 scale)",
            "scoring_process": {
                "step_1": "Domain Score Calculation - Confidence-weighted average of normalized benchmarks per domain",
                "step_2": "Profile Weight Application - Domain scores weighted by professional profile preferences", 
                "step_3": "Weight Redistribution - Missing domains' weights redistributed proportionally",
                "step_4": "Confidence Adjustment - Overall confidence adjusted by domain coverage",
                "step_5": "Final Composite Score - Weighted average with transparency metrics"
            },
            "professional_profiles": {
                "General": "Balanced evaluation (20% each major domain)",
                "Academic": "Research focus (35% academic, 25% reasoning, 25% comprehensive)",
                "Developer": "Coding focus (40% software engineering, 30% reasoning)",
                "Healthcare": "Medical focus (35% medical, 25% reasoning)",
                "Legal": "Legal focus (35% legal, 20% academic/comprehensive)"
            },
            "quality_assurance": {
                "statistical_validation": "Minimum 2 domains required, confidence scoring",
                "transparency": "Full calculation breakdown available per model",
                "data_authenticity": "100% research-grade evaluation standards",
                "methodology_peer_review": "Academic-grade normalization and weighting"
            },
            "interpretation": {
                "score_range": "0-100 (higher is better)",
                "confidence_range": "0-1 (higher is more reliable)", 
                "domain_coverage": "1-6 domains (more domains = more reliable composite)",
                "comparison_validity": "Scores comparable within and across profiles"
            }
        }
    } 