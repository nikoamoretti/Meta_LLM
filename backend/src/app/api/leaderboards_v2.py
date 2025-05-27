from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Dict, Optional

from ..database import get_db
from ...db.db_models import Model, Benchmark, Score
from .models import ModelScore, ModelDetailResponse

router = APIRouter()

@router.get("/models", response_model=List[ModelScore])
def get_models(db: Session = Depends(get_db)):
    """Get all models with their scores"""
    
    # Get all models
    models = db.query(Model).all()
    
    result = []
    for model in models:
        # Get all scores for this model
        scores = db.query(Score, Benchmark).join(Benchmark).filter(
            Score.model_id == model.id
        ).all()
        
        if not scores:
            continue
        
        # Organize scores by category
        category_scores = {}
        benchmark_details = {
            'code_benchmarks': {},
            'medical_benchmarks': {},
            'legal_benchmarks': {}
        }
        
        overall_score = None
        benchmark_count = 0
        
        for score, benchmark in scores:
            # Skip composite scores for individual benchmark count
            if 'composite' not in benchmark.name:
                benchmark_count += 1
            
            # Handle composite scores
            if benchmark.name == 'overall_composite':
                overall_score = score.normalized_value or score.value
            elif benchmark.name.endswith('_composite'):
                category = benchmark.name.replace('_composite', '')
                category_scores[category] = score.normalized_value or score.value
            else:
                # Individual benchmark scores
                if benchmark.category == 'code':
                    benchmark_details['code_benchmarks'][benchmark.name] = round(score.normalized_value or score.value, 1)
                elif benchmark.category == 'medical':
                    benchmark_details['medical_benchmarks'][benchmark.name] = round(score.normalized_value or score.value, 1)
                elif benchmark.category == 'legal':
                    benchmark_details['legal_benchmarks'][benchmark.name] = round(score.normalized_value or score.value, 1)
        
        # If no overall score, calculate it
        if overall_score is None and category_scores:
            overall_score = sum(category_scores.values()) / len(category_scores)
        elif overall_score is None:
            # Calculate from all normalized scores
            all_normalized = [s.normalized_value for s, b in scores if s.normalized_value is not None and 'composite' not in b.name]
            if all_normalized:
                overall_score = sum(all_normalized) / len(all_normalized)
            else:
                overall_score = 0.0
        
        model_score = ModelScore(
            model=model.name,
            overall=round(overall_score, 2),
            benchmark_count=benchmark_count,
            
            # Core categories
            code=category_scores.get('code'),
            hallucination=category_scores.get('hallucination'),
            medical=category_scores.get('medical'),
            legal=category_scores.get('legal'),
            multilingual=category_scores.get('multilingual'),
            
            # Extended categories
            chinese=category_scores.get('chinese'),
            emotional=category_scores.get('emotional'),
            instruction=category_scores.get('instruction'),
            finance=category_scores.get('finance'),
            general=category_scores.get('general'),
            
            # Benchmark details
            code_benchmarks=benchmark_details['code_benchmarks'] if benchmark_details['code_benchmarks'] else None,
            medical_benchmarks=benchmark_details['medical_benchmarks'] if benchmark_details['medical_benchmarks'] else None,
            legal_benchmarks=benchmark_details['legal_benchmarks'] if benchmark_details['legal_benchmarks'] else None,
        )
        result.append(model_score)
    
    # Sort by overall score descending and assign global ranks
    result.sort(key=lambda x: x.overall, reverse=True)
    for i, model in enumerate(result):
        model.global_rank = i + 1
    
    # Return only top 100 models for better performance
    return result[:100]

@router.get("/models/{name}", response_model=ModelDetailResponse)
def get_model_detail(name: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific model"""
    
    # Get the model
    model = db.query(Model).filter(Model.name == name).first()
    
    if not model:
        return ModelDetailResponse(
            model=name,
            overall=0.0,
            global_rank=None,
            benchmarks=[],
            history=[],
            benchmark_count=0
        )
    
    # Get all scores for this model
    scores = db.query(Score, Benchmark).join(Benchmark).filter(
        Score.model_id == model.id
    ).all()
    
    # Organize scores
    category_scores = {}
    benchmarks = []
    overall_score = None
    benchmark_count = 0
    
    for score, benchmark in scores:
        if 'composite' not in benchmark.name:
            benchmark_count += 1
            
            benchmarks.append({
                "name": benchmark.name,
                "benchmark": benchmark.name,
                "metric": benchmark.name,
                "score": round(score.normalized_value or score.value, 2),
                "raw_score": score.value,
                "higher_is_better": True,  # Default, could be stored in benchmark
                "category": benchmark.category
            })
        
        # Handle composite scores
        if benchmark.name == 'overall_composite':
            overall_score = score.normalized_value or score.value
        elif benchmark.name.endswith('_composite'):
            category = benchmark.name.replace('_composite', '')
            category_scores[category] = score.normalized_value or score.value
    
    # If no overall score, calculate it
    if overall_score is None:
        if category_scores:
            overall_score = sum(category_scores.values()) / len(category_scores)
        else:
            all_normalized = [s.normalized_value for s, b in scores if s.normalized_value is not None and 'composite' not in b.name]
            if all_normalized:
                overall_score = sum(all_normalized) / len(all_normalized)
            else:
                overall_score = 0.0
    
    # Get global rank
    all_models = get_models(db)
    global_rank = None
    for i, m in enumerate(all_models):
        if m.model == name:
            global_rank = i + 1
            break
    
    return ModelDetailResponse(
        model=name,
        overall=round(overall_score, 2),
        global_rank=global_rank,
        benchmark_count=benchmark_count,
        
        # Category scores
        code=category_scores.get('code'),
        hallucination=category_scores.get('hallucination'),
        medical=category_scores.get('medical'),
        legal=category_scores.get('legal'),
        multilingual=category_scores.get('multilingual'),
        chinese=category_scores.get('chinese'),
        emotional=category_scores.get('emotional'),
        instruction=category_scores.get('instruction'),
        finance=category_scores.get('finance'),
        general=category_scores.get('general'),
        
        benchmarks=benchmarks,
        history=[]  # TODO: Implement historical data
    )

@router.get("/leaderboards")
def get_leaderboards(db: Session = Depends(get_db)):
    """Get all available leaderboards/categories"""
    
    # Get unique benchmark categories
    categories = db.query(Benchmark.category).distinct().all()
    
    result = []
    for (category,) in categories:
        # Count benchmarks in this category
        count = db.query(func.count(Benchmark.id)).filter(
            Benchmark.category == category
        ).scalar()
        
        result.append({
            "id": len(result) + 1,
            "name": category.replace('_', ' ').title(),
            "category": category,
            "benchmark_count": count
        })
    
    return result 