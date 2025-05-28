"""
Leaderboards API v3 - Universal Normalization Framework
Enhanced endpoints with normalized scoring, confidence metrics, and transparency

This implements the API integration layer for Task 5.1 normalization framework.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
from datetime import datetime

from ..database import get_db
from ...db.models import Leaderboard, RawScore, NormalizedScore
from ...services.normalization_service import NormalizationService
from .models import (
    NormalizedModelScore, DetailedScoreResponse, NormalizationStats, 
    ProcessingReportResponse, CategoryScore
)

router = APIRouter()

# Initialize normalization service
normalization_service = NormalizationService()

@router.get("/models/normalized", response_model=List[NormalizedModelScore])
def get_normalized_models(limit: int = 100, db: Session = Depends(get_db)):
    """Return models with advanced normalized scoring"""
    
    try:
        # Get all unique models with their normalized scores
        model_data = db.query(
            RawScore.model_name,
            func.count(RawScore.id).label('benchmark_count'),
            func.avg(NormalizedScore.normalized_value).label('avg_normalized'),
            func.avg(NormalizedScore.confidence_score).label('avg_confidence'),
            func.max(NormalizedScore.updated_at).label('last_updated')
        ).join(NormalizedScore, RawScore.id == NormalizedScore.raw_score_id)\
         .group_by(RawScore.model_name)\
         .order_by(func.avg(NormalizedScore.normalized_value).desc())\
         .limit(limit).all()
        
        if not model_data:
            return []
        
        results = []
        for i, model in enumerate(model_data):
            # Get category scores for this model
            category_scores = get_model_category_scores(db, model.model_name)
            
            # Determine quality level
            quality = "HIGH" if model.avg_confidence >= 0.9 else "MEDIUM" if model.avg_confidence >= 0.7 else "LOW"
            
            normalized_model = NormalizedModelScore(
                model=model.model_name,
                overall_normalized=round(model.avg_normalized, 2),
                overall_confidence=round(model.avg_confidence, 3),
                global_rank=i + 1,
                category_scores=category_scores,
                normalization_quality=quality,
                benchmark_count=model.benchmark_count,
                last_updated=model.last_updated.isoformat() if model.last_updated else datetime.now().isoformat()
            )
            results.append(normalized_model)
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get normalized models: {str(e)}")

@router.get("/models/{model_name}/scores/detailed", response_model=DetailedScoreResponse)
def get_detailed_scores(model_name: str, db: Session = Depends(get_db)):
    """Raw + normalized + confidence for all scores of a specific model"""
    
    try:
        # Get all scores for this model with normalization data
        scores = db.query(
            RawScore.value,
            RawScore.metric,
            RawScore.benchmark,
            NormalizedScore.normalized_value,
            NormalizedScore.confidence_score,
            NormalizedScore.normalization_method,
            NormalizedScore.updated_at,
            Leaderboard.name.label('leaderboard_name'),
            Leaderboard.category
        ).join(NormalizedScore, RawScore.id == NormalizedScore.raw_score_id)\
         .join(Leaderboard, RawScore.leaderboard_id == Leaderboard.id)\
         .filter(RawScore.model_name == model_name).all()
        
        if not scores:
            raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
        
        # Build benchmark details
        benchmark_details = []
        for score in scores:
            benchmark_details.append({
                "leaderboard": score.leaderboard_name,
                "benchmark": score.benchmark,
                "metric": score.metric,
                "raw_score": score.value,
                "normalized_score": round(score.normalized_value, 2),
                "confidence": round(score.confidence_score, 3),
                "normalization_method": score.normalization_method,
                "category": score.category
            })
        
        # Calculate category summaries
        category_summaries = get_model_category_scores(db, model_name)
        
        # Calculate overall metrics
        overall_normalized = sum(s.normalized_value for s in scores) / len(scores)
        overall_confidence = sum(s.confidence_score for s in scores) / len(scores)
        
        # Quality score calculation
        quality_score = calculate_model_quality_score(scores)
        
        # Get global rank
        global_rank = get_model_global_rank(db, model_name)
        
        return DetailedScoreResponse(
            model=model_name,
            overall_normalized=round(overall_normalized, 2),
            overall_confidence=round(overall_confidence, 3),
            global_rank=global_rank,
            benchmark_details=benchmark_details,
            category_summaries=category_summaries,
            total_benchmarks=len(scores),
            normalization_quality_score=quality_score,
            last_normalization_update=max(s.updated_at for s in scores).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get detailed scores: {str(e)}")

@router.get("/normalization/statistics", response_model=NormalizationStats)
def get_normalization_statistics(db: Session = Depends(get_db)):
    """Platform-wide normalization quality metrics"""
    
    try:
        stats = normalization_service.get_normalization_statistics()
        
        if 'error' in stats:
            raise HTTPException(status_code=500, detail=stats['error'])
        
        return NormalizationStats(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@router.post("/normalization/process-all", response_model=ProcessingReportResponse)
def process_all_scores():
    """Batch normalize all existing scores (admin endpoint)"""
    
    try:
        report = normalization_service.normalize_all_scores()
        
        return ProcessingReportResponse(
            total_scores=report.total_scores,
            processed_scores=report.processed_scores,
            failed_scores=report.failed_scores,
            average_confidence=report.average_confidence,
            processing_time=report.processing_time,
            success_rate=(report.processed_scores / report.total_scores * 100) if report.total_scores > 0 else 0,
            errors=report.errors
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

@router.get("/normalization/validation")
def validate_normalization_quality():
    """Validate normalization quality across all scores"""
    
    try:
        validation_results = normalization_service.validate_normalization_quality()
        
        if 'error' in validation_results:
            raise HTTPException(status_code=500, detail=validation_results['error'])
        
        return validation_results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

# Helper functions

def get_model_category_scores(db: Session, model_name: str) -> Dict[str, CategoryScore]:
    """Get category-specific scores for a model"""
    
    category_data = db.query(
        Leaderboard.category,
        func.avg(NormalizedScore.normalized_value).label('avg_normalized'),
        func.avg(NormalizedScore.confidence_score).label('avg_confidence'),
        func.count(NormalizedScore.id).label('benchmark_count'),
        func.avg(RawScore.value).label('avg_raw')
    ).join(RawScore, NormalizedScore.raw_score_id == RawScore.id)\
     .join(Leaderboard, RawScore.leaderboard_id == Leaderboard.id)\
     .filter(RawScore.model_name == model_name)\
     .group_by(Leaderboard.category).all()
    
    category_scores = {}
    for cat_data in category_data:
        category_scores[cat_data.category] = CategoryScore(
            normalized_score=round(cat_data.avg_normalized, 2),
            confidence=round(cat_data.avg_confidence, 3),
            benchmark_count=cat_data.benchmark_count,
            raw_score_avg=round(cat_data.avg_raw, 2) if cat_data.avg_raw else None
        )
    
    return category_scores

def calculate_model_quality_score(scores) -> float:
    """Calculate overall quality score for a model's normalizations"""
    
    if not scores:
        return 0.0
    
    # Base quality from average confidence
    avg_confidence = sum(s.confidence_score for s in scores) / len(scores)
    
    # Penalty for low confidence scores
    low_confidence_count = sum(1 for s in scores if s.confidence_score < 0.7)
    low_confidence_penalty = (low_confidence_count / len(scores)) * 0.2
    
    # Bonus for high benchmark coverage
    coverage_bonus = min(0.1, len(scores) / 100)  # Up to 10% bonus for 100+ benchmarks
    
    quality_score = avg_confidence - low_confidence_penalty + coverage_bonus
    
    return max(0.0, min(1.0, quality_score))

def get_model_global_rank(db: Session, model_name: str) -> Optional[int]:
    """Get global ranking for a model"""
    
    try:
        ranked_models = db.query(
            RawScore.model_name,
            func.avg(NormalizedScore.normalized_value).label('avg_score')
        ).join(NormalizedScore, RawScore.id == NormalizedScore.raw_score_id)\
         .group_by(RawScore.model_name)\
         .order_by(func.avg(NormalizedScore.normalized_value).desc()).all()
        
        for i, model in enumerate(ranked_models):
            if model.model_name == model_name:
                return i + 1
        
        return None
        
    except Exception:
        return None 