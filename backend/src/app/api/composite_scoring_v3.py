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

def get_benchmark_description(benchmark_name: str) -> str:
    """Get description for benchmark"""
    descriptions = {
        "SWE-Bench": "Real-world GitHub software engineering issue resolution (500 verified issues)",
        "HumanEval": "Hand-written programming problems for measuring functional correctness",
        "MBPP": "Mostly Basic Python Problems - entry-level programming challenges",
        "BigCode": "BigCode Models Leaderboard - comprehensive coding evaluation across multiple programming languages",
        "EvalPlus": "EvalPlus enhanced HumanEval+ and MBPP+ with rigorous test cases",
        "Aider.chat": "Code editing performance across 6 programming languages",
        "Can-AI-Code": "Can-AI-Code leaderboard - evaluating LLMs on coding tasks and programming challenges",
        "Convex": "Convex.dev LLM Leaderboard - coding performance evaluation",
        "LiveBench": "Real-time evaluation with challenging, contamination-free benchmarks updated monthly",
        "LM Arena WebDev": "Web development coding evaluation including HTML, CSS, JavaScript, and full-stack development",
        "ProllM StackEval": "Stack-based programming challenges and algorithmic problem solving evaluation",
        "CruxEval": "Code reasoning benchmark complementary to HumanEval and MBPP focusing on code understanding",
        "ClassEval": "Class-level code generation benchmark for object-oriented programming evaluation",
        "CodeTLingua": "Multilingual code generation benchmark across different programming languages",
        "DS-1000": "Data science code generation benchmark with realistic pandas, numpy, and ML library tasks",
        "EvoEval": "Evolving code evaluation benchmark to prevent contamination and maintain challenge level",
        "TabbyML": "Code completion and AI-assisted development evaluation benchmark"
    }
    return descriptions.get(benchmark_name, f"Coding benchmark: {benchmark_name}")

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
            # Return empty response instead of error for clean restart
            return {
                "profile_name": profile_name,
                "total_models": 0,
                "generated_at": datetime.now().isoformat(),
                "leaderboard": [],
                "message": "Composite scoring temporarily disabled - use /api/v3/coding/ endpoints for raw benchmark data"
            }
        
        return {
            "profile_name": profile_name,
            "total_models": len(leaderboard),
            "generated_at": datetime.now().isoformat(),
            "leaderboard": leaderboard
        }
        
    except Exception as e:
        # Return empty response instead of error for clean restart
        return {
            "profile_name": profile_name,
            "total_models": 0,
            "generated_at": datetime.now().isoformat(),
            "leaderboard": [],
            "message": "Composite scoring temporarily disabled - use /api/v3/coding/ endpoints for raw benchmark data"
        }

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

@router.get("/models/{model_name}/benchmarks")
async def get_model_individual_benchmarks(
    model_name: str,
    category: Optional[str] = Query(None, description="Filter by category (e.g., 'software_engineering', 'coding')")
):
    """
    Get individual benchmark scores for a specific model
    
    This endpoint exposes the raw benchmark data that gets aggregated into domain scores,
    allowing users to see HumanEval, MBPP, SWE-Bench, etc. individual results.
    """
    try:
        benchmarks = composite_service.get_model_individual_benchmarks(model_name, category)
        
        if not benchmarks:
            raise HTTPException(status_code=404, detail=f"No benchmark data found for model: {model_name}")
        
        return {
            "model_name": model_name,
            "total_benchmarks": len(benchmarks),
            "category_filter": category,
            "benchmarks": benchmarks,
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve benchmarks: {str(e)}")

@router.get("/category/{category_name}/benchmarks")
async def get_category_benchmark_breakdown(
    category_name: str,
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get individual benchmark breakdown for all models in a category
    
    This shows how each model performs on individual benchmarks that make up 
    the category's domain score aggregation.
    """
    try:
        breakdown = composite_service.get_category_benchmark_breakdown(category_name, limit)
        
        if not breakdown:
            raise HTTPException(status_code=404, detail=f"No benchmark data found for category: {category_name}")
        
        return {
            "category_name": category_name,
            "total_models": len(breakdown.get('models', [])),
            "benchmarks_in_category": breakdown.get('benchmarks', []),
            "models": breakdown.get('models', []),
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve category breakdown: {str(e)}")

@router.get("/coding/benchmarks")
async def get_coding_benchmarks(limit: int = Query(1000, ge=1, le=2000)):
    """
    Get individual benchmark scores for coding/software engineering models
    
    Returns all models with their individual coding benchmark scores 
    (HumanEval, MBPP, CodeContests, SWE-Bench, Programming)
    """
    try:
        import sqlite3
        from collections import defaultdict
        
        # Get data from BOTH databases - old data and new scraper data
        results = []
        
        # 1. Get existing data from old database (excluding file names and directories)
        conn_old = sqlite3.connect("meta_llm.db")
        conn_old.row_factory = sqlite3.Row
        cursor_old = conn_old.cursor()
        
        # File extensions and directory names to exclude
        file_patterns = [
            '%.py', '%.sh', '%.txt', '%.md', '%.gitignore', '%.js', '%.json', 
            '%.yml', '%.yaml', '%.xml', '%.csv', '%.log'
        ]
        
        directory_names = [
            'senior', 'sbox', 'results', 'prompts', 'params', 'models', 
            'junior-v2', 'img', 'humaneval', 'compare', 'compare-v1',
            'requirements-exl2', 'requirements-transformers', 'requirements-vllm'
        ]
        
        # Build exclusion conditions for old database (with rs. prefix)
        like_conditions_old = " AND ".join([f"rs.model_name NOT LIKE '{pattern}'" for pattern in file_patterns])
        not_in_conditions_old = "'" + "','".join(directory_names) + "'"
        
        # Build exclusion conditions for new database (without rs. prefix)
        like_conditions_new = " AND ".join([f"model_name NOT LIKE '{pattern}'" for pattern in file_patterns])
        not_in_conditions_new = "'" + "','".join(directory_names) + "'"
        
        cursor_old.execute(f"""
            SELECT 
                rs.model_name,
                rs.benchmark,
                rs.value as raw_score,
                COALESCE(ns.normalized_value, rs.value) as normalized_score,
                l.name as leaderboard_name,
                l.category
            FROM raw_scores rs
            LEFT JOIN normalized_scores ns ON rs.id = ns.raw_score_id
            JOIN leaderboards l ON rs.leaderboard_id = l.id
            WHERE l.category IN ('software_engineering', 'coding', 'programming')
            AND {like_conditions_old}
            AND rs.model_name NOT IN ({not_in_conditions_old})
            AND rs.model_name NOT LIKE 'Bracket.%'
            ORDER BY rs.model_name, rs.benchmark
        """)
        
        results.extend(cursor_old.fetchall())
        conn_old.close()
        
        # 2. Get ALL NEW coding benchmark data from coding_benchmarks table (with filtering)
        try:
            conn_new = sqlite3.connect("/app/src/db/meta_llm_leaderboard.db")
            conn_new.row_factory = sqlite3.Row
            cursor_new = conn_new.cursor()
            
            # Get ALL coding benchmarks: SWE-Bench, BigCode, EvalPlus (excluding file names and low-quality entries)
            cursor_new.execute(f"""
                SELECT 
                    model_name,
                    metric as benchmark,
                    score as raw_score,
                    score as normalized_score,
                    benchmark_name as leaderboard_name,
                    'software_engineering' as category
                FROM coding_benchmarks
                WHERE {like_conditions_new}
                AND model_name NOT IN ({not_in_conditions_new})
                AND model_name NOT LIKE 'Bracket.%'
                AND model_name NOT LIKE '%zyte-1B%'
                AND model_name NOT LIKE '%Anthopic%'
                AND score > 0
                ORDER BY model_name, benchmark_name
            """)
            
            new_results = cursor_new.fetchall()
            print(f"Loaded {len(new_results)} entries from new coding_benchmarks table")
            results.extend(new_results)
            conn_new.close()
            
        except Exception as e:
            print(f"Could not load new coding benchmark data: {e}")
            # Continue with just old data if new data fails
        
        # Group by model with deduplication
        models_data = defaultdict(lambda: {'model_name': '', 'benchmarks': {}, 'average_score': 0})
        
        def normalize_model_name(name):
            """Normalize model names to handle common typos and variations"""
            # Fix common typos
            name = name.replace('Anthopic', 'Anthropic')
            # Remove incomplete entries indicator
            if name.endswith(' + Deepseek V3') and name.startswith('Moatless Tools'):
                return None  # Filter out incomplete entries
            return name
        
        for row in results:
            model_name = normalize_model_name(row['model_name'])
            if model_name is None:
                continue  # Skip filtered entries
                
            models_data[model_name]['model_name'] = model_name
            
            # Use leaderboard name for better identification
            leaderboard_name = row['leaderboard_name']
            benchmark_key = row['benchmark']
            
            # Map specific leaderboards to standardized names for frontend
            if 'Aider' in leaderboard_name:
                benchmark_key = 'Aider.chat'
            elif 'SWE-Bench' in leaderboard_name:
                benchmark_key = 'SWE-Bench'
            elif 'BigCode' in leaderboard_name:
                benchmark_key = 'BigCode'
            elif 'EvalPlus' in leaderboard_name:
                # For EvalPlus, use the specific metric as benchmark name for better granularity
                if 'humaneval' in benchmark_key.lower():
                    benchmark_key = 'HumanEval'
                elif 'mbpp' in benchmark_key.lower():
                    benchmark_key = 'MBPP'
                else:
                    benchmark_key = 'EvalPlus'
            elif 'Can-AI-Code' in leaderboard_name:
                benchmark_key = 'Can-AI-Code'
            elif 'Convex' in leaderboard_name:
                benchmark_key = 'Convex'
            elif 'LiveBench' in leaderboard_name:
                benchmark_key = 'LiveBench'
            elif 'LM Arena WebDev' in leaderboard_name or 'lmarena' in leaderboard_name.lower():
                benchmark_key = 'LM Arena WebDev'
            elif 'ProllM' in leaderboard_name or 'StackEval' in leaderboard_name:
                benchmark_key = 'ProllM StackEval'
            elif 'CruxEval' in leaderboard_name:
                benchmark_key = 'CruxEval'
            elif 'ClassEval' in leaderboard_name:
                benchmark_key = 'ClassEval'
            elif 'CodeTLingua' in leaderboard_name:
                benchmark_key = 'CodeTLingua'
            elif 'DS-1000' in leaderboard_name or 'DS1000' in leaderboard_name:
                benchmark_key = 'DS-1000'
            elif 'EvoEval' in leaderboard_name:
                benchmark_key = 'EvoEval'
            elif 'TabbyML' in leaderboard_name:
                benchmark_key = 'TabbyML'
            
            models_data[model_name]['benchmarks'][benchmark_key] = row['normalized_score']
        
        # Calculate average scores and sort
        for model_name, data in models_data.items():
            scores = [score for score in data['benchmarks'].values() if score is not None]
            data['average_score'] = sum(scores) / len(scores) if scores else 0
        
        # Sort by average score and limit results
        sorted_models = sorted(
            models_data.values(), 
            key=lambda x: x['average_score'], 
            reverse=True
        )[:limit]
        
        # Get list of all available benchmarks with source URLs
        available_benchmarks = set()
        for model in sorted_models:
            available_benchmarks.update(model['benchmarks'].keys())
        
        # Add benchmark metadata with source URLs
        benchmark_sources = {
            "SWE-Bench": "https://www.swebench.com/",
            "HumanEval": "https://github.com/openai/human-eval",
            "MBPP": "https://github.com/google-research/google-research/tree/master/mbpp",
            "BigCode": "https://huggingface.co/spaces/bigcode/bigcode-models-leaderboard",
            "EvalPlus": "https://evalplus.github.io/leaderboard",
            "Aider.chat": "https://aider.chat/docs/leaderboards/",
            "Can-AI-Code": "https://huggingface.co/spaces/mike-ravkine/can-ai-code-results",
            "Convex": "https://www.convex.dev/llm-leaderboard",
            "LiveBench": "https://livebench.ai/#/",
            "LM Arena WebDev": "https://lmarena.ai/leaderboard/webdev",
            "ProllM StackEval": "https://www.prollm.ai/leaderboard/stack-eval",
            "CruxEval": "https://crux-eval.github.io/leaderboard.html",
            "ClassEval": "https://fudanselab-classeval.github.io/leaderboard.html",
            "CodeTLingua": "https://codetlingua.github.io/leaderboard.html",
            "DS-1000": "https://ds1000-code-gen.github.io/model_DS1000.html",
            "EvoEval": "https://evo-eval.github.io/leaderboard.html",
            "TabbyML": "https://leaderboard.tabbyml.com/"
        }
        
        benchmark_info = []
        for benchmark in sorted(available_benchmarks):
            benchmark_info.append({
                "name": benchmark,
                "source_url": benchmark_sources.get(benchmark, ""),
                "description": get_benchmark_description(benchmark)
            })
        
        return {
            "category": "coding",
            "total_models": len(sorted_models),
            "available_benchmarks": benchmark_info,
            "models": sorted_models,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve coding benchmarks: {str(e)}") 