from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from ..database import get_db
from ...db.models import Leaderboard, RawScore
from .models import ModelScore, ModelDetailResponse

router = APIRouter()

def normalize_score(value, metric, leaderboard_name, higher_is_better=True):
    """
    Normalize scores to 0-100 scale based on metric type and known ranges
    """
    # Define known score ranges for different metrics
    score_ranges = {
        'elo_rating': (800, 1400),  # ELO ratings
        'daily_requests': (0, 500000),  # Request counts
        'hallucination_rate': (0, 20),  # Percentage where lower is better
        'accuracy': (0, 100),  # Already 0-100
        'pass@1': (0, 100),  # Already 0-100
        'win_rate': (0, 100),  # Already 0-100
        'composite_score': (0, 100),  # Already 0-100
        'eq_score': (0, 100),  # Already 0-100
        'average': (0, 100),  # Already 0-100
        # Code metrics - all are percentages 0-100
        'humaneval': (0, 100),
        'humaneval_pass@1': (0, 100),
        'mbpp': (0, 100),
        'mbpp_pass@1': (0, 100),
        'apps': (0, 100),
        'humaneval+': (0, 100),
        'mbpp+': (0, 100),
        'multipl-e': (0, 100),
        'pass_rate': (0, 100),
        # Math/reasoning metrics
        'gsm8k': (0, 100),
        'math': (0, 100),
        'aime_2024': (0, 100),
        'gpqa_diamond': (0, 100),
        # Knowledge metrics
        'mmlu': (0, 100),
        'arc': (0, 100),
        'arc_challenge': (0, 100),
        'hellaswag': (0, 100),
        'truthfulqa': (0, 100),
        'winogrande': (0, 100),
        # Medical metrics
        'medqa': (0, 100),
        'medmcqa': (0, 100),
        'pubmedqa': (0, 100),
        'mmlu_medical': (0, 100),
        # Legal metrics
        'legalbench': (0, 100),
        'bar_exam': (0, 100),
        # Finance metrics
        'finqa': (0, 100),
        'financial_sentiment': (0, 100),
        # Multilingual metrics
        'multilingual_mmlu': (0, 100),
        'xquad': (0, 100),
        'c_eval': (0, 100),
        # Other metrics
        'mt_bench': (0, 10),  # MT-Bench is 0-10 scale
        'bigbench_hard': (0, 100),
        'eq_bench': (0, 100),
        'klu_index': (0, 100),
        'tokens_served': (0, 100000000000),  # 100 billion tokens max
        'usage_percentage': (0, 100),
        'cost_per_token': (0, 0.1),  # $0.10 per token max
    }
    
    # Get the range for this metric
    metric_lower = metric.lower()
    if metric_lower in score_ranges:
        min_val, max_val = score_ranges[metric_lower]
    elif 'elo' in metric_lower or 'rating' in metric_lower:
        min_val, max_val = 800, 1400
    elif any(term in metric_lower for term in ['accuracy', 'score', 'rate', 'pass', 'eval']):
        # Most metrics with these terms are percentages
        min_val, max_val = 0, 100
    else:
        # Default to 0-100 for unknown metrics
        min_val, max_val = 0, 100
    
    # Normalize to 0-100 scale
    if max_val > min_val:
        normalized = ((value - min_val) / (max_val - min_val)) * 100
    else:
        normalized = value
    
    # Handle "lower is better" metrics
    if not higher_is_better or metric_lower in ['hallucination_rate', 'perplexity', 'loss', 'error']:
        normalized = 100 - normalized
    
    # Clamp to 0-100 range
    return max(0, min(100, normalized))

@router.get("/leaderboards")
def get_leaderboards(db: Session = Depends(get_db)):
    leaderboards = db.query(Leaderboard).all()
    return [{"id": lb.id, "name": lb.name, "category": lb.category} for lb in leaderboards]

def get_category_score(db: Session, model_name: str, category: str):
    """Helper function to get normalized average score for a model in a specific category"""
    scores = db.query(
        RawScore.value,
        RawScore.metric,
        RawScore.higher_is_better,
        Leaderboard.name
    ).join(Leaderboard).filter(
        RawScore.model_name == model_name,
        Leaderboard.category == category
    ).all()
    
    if not scores:
        return None
    
    # Normalize each score and calculate average
    normalized_scores = []
    for value, metric, higher_is_better, leaderboard_name in scores:
        normalized = normalize_score(value, metric, leaderboard_name, higher_is_better)
        normalized_scores.append(normalized)
    
    return round(sum(normalized_scores) / len(normalized_scores), 2) if normalized_scores else None

def get_category_benchmarks(db: Session, model_name: str, category: str):
    """Get individual benchmark scores for a model in a specific category"""
    scores = db.query(
        RawScore.metric,
        RawScore.value,
        RawScore.higher_is_better,
        Leaderboard.name
    ).join(Leaderboard).filter(
        RawScore.model_name == model_name,
        Leaderboard.category == category
    ).all()
    
    if not scores:
        return None
    
    # Group by benchmark and normalize
    benchmarks = {}
    for metric, value, higher_is_better, leaderboard_name in scores:
        normalized = normalize_score(value, metric, leaderboard_name, higher_is_better)
        # Create a readable benchmark name
        benchmark_key = f"{leaderboard_name} - {metric}"
        benchmarks[benchmark_key] = round(normalized, 1)
    
    return benchmarks

@router.get("/models", response_model=List[ModelScore])
def get_models(db: Session = Depends(get_db)):
    # Get all unique models
    models_data = db.query(RawScore.model_name).distinct().all()
    
    result = []
    for (model_name,) in models_data:
        # Get all scores for this model
        scores = db.query(
            RawScore.value,
            RawScore.metric,
            RawScore.higher_is_better,
            Leaderboard.name,
            Leaderboard.category
        ).join(Leaderboard).filter(
            RawScore.model_name == model_name
        ).all()
        
        if not scores:
            continue
        
        # Calculate normalized overall score
        normalized_scores = []
        benchmark_count = len(scores)
        
        # Track category coverage
        categories_covered = set()
        
        for value, metric, higher_is_better, leaderboard_name, category in scores:
            normalized = normalize_score(value, metric, leaderboard_name, higher_is_better)
            normalized_scores.append(normalized)
            categories_covered.add(category)
        
        # Calculate base score
        base_score = sum(normalized_scores) / len(normalized_scores) if normalized_scores else 0.0
        
        # Apply coverage penalty/bonus
        # Models with fewer than 10 benchmarks get penalized
        # Models with good category coverage get a bonus
        coverage_factor = 1.0
        
        if benchmark_count < 10:
            # Penalty for too few benchmarks (up to 20% penalty)
            coverage_factor = 0.8 + (benchmark_count / 50.0)
        elif benchmark_count >= 20:
            # Small bonus for comprehensive evaluation (up to 5% bonus)
            coverage_factor = 1.0 + min(0.05, (benchmark_count - 20) / 200.0)
        
        # Category diversity bonus (up to 5% bonus)
        category_bonus = min(0.05, len(categories_covered) / 20.0)
        
        # Calculate final overall score
        overall_score = base_score * coverage_factor * (1 + category_bonus)
        overall_score = round(min(100, overall_score), 2)  # Cap at 100
        
        # Get all category-specific scores
        model_score = ModelScore(
            model=model_name,
            overall=overall_score,
            benchmark_count=benchmark_count,
            
            # Core categories
            code=get_category_score(db, model_name, 'code'),
            hallucination=get_category_score(db, model_name, 'hallucination'),
            medical=get_category_score(db, model_name, 'medical'),
            legal=get_category_score(db, model_name, 'legal'),
            multilingual=get_category_score(db, model_name, 'multilingual'),
            
            # Extended categories
            chinese=get_category_score(db, model_name, 'chinese'),
            emotional=get_category_score(db, model_name, 'emotional'),
            instruction=get_category_score(db, model_name, 'instruction'),
            finance=get_category_score(db, model_name, 'finance'),
            general=get_category_score(db, model_name, 'general'),
            
            # Add benchmark breakdowns
            code_benchmarks=get_category_benchmarks(db, model_name, 'code'),
            medical_benchmarks=get_category_benchmarks(db, model_name, 'medical'),
            legal_benchmarks=get_category_benchmarks(db, model_name, 'legal'),
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
    # Get model scores with leaderboard info
    model_scores = db.query(
        RawScore.value,
        RawScore.metric,
        RawScore.higher_is_better,
        RawScore.benchmark,
        RawScore.leaderboard_id,
        Leaderboard.name.label('leaderboard_name'),
        Leaderboard.category
    ).join(Leaderboard).filter(RawScore.model_name == name).all()
    
    if not model_scores:
        return ModelDetailResponse(
            model=name,
            overall=0.0,
            global_rank=None,
            code=None,
            hallucination=None,
            medical=None,
            legal=None,
            multilingual=None,
            chinese=None,
            emotional=None,
            instruction=None,
            finance=None,
            general=None,
            benchmarks=[],
            history=[],
            benchmark_count=0
        )
    
    # Calculate normalized overall score
    normalized_scores = []
    benchmarks = []
    
    for value, metric, higher_is_better, benchmark, leaderboard_id, leaderboard_name, category in model_scores:
        normalized = normalize_score(value, metric, leaderboard_name, higher_is_better)
        normalized_scores.append(normalized)
        
        benchmarks.append({
            "name": leaderboard_name,
            "benchmark": benchmark,
            "metric": metric,
            "score": round(normalized, 2),  # Return normalized score
            "raw_score": value,  # Also include raw score for reference
            "higher_is_better": higher_is_better,
            "category": category
        })
    
    overall = round(sum(normalized_scores) / len(normalized_scores), 2) if normalized_scores else 0.0
    
    # Get global rank
    all_models = get_models(db)
    global_rank = None
    for i, model in enumerate(all_models):
        if model.model == name:
            global_rank = i + 1
            break
    
    return ModelDetailResponse(
        model=name,
        overall=overall,
        global_rank=global_rank,
        benchmark_count=len(model_scores),
        
        # Category scores
        code=get_category_score(db, name, 'code'),
        hallucination=get_category_score(db, name, 'hallucination'),
        medical=get_category_score(db, name, 'medical'),
        legal=get_category_score(db, name, 'legal'),
        multilingual=get_category_score(db, name, 'multilingual'),
        chinese=get_category_score(db, name, 'chinese'),
        emotional=get_category_score(db, name, 'emotional'),
        instruction=get_category_score(db, name, 'instruction'),
        finance=get_category_score(db, name, 'finance'),
        general=get_category_score(db, name, 'general'),
        
        benchmarks=benchmarks,
        history=[]  # TODO: Implement historical data
    ) 