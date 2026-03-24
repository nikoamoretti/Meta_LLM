"""
Simple Coding Leaderboard API
Clean implementation without composite scoring - just raw benchmark results
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime
import sqlite3
from collections import defaultdict

router = APIRouter()

@router.get("/coding/all-benchmarks")
async def get_all_coding_benchmarks(
    limit: int = Query(50, ge=1, le=200),
    benchmark: Optional[str] = Query(None, description="Filter by specific benchmark")
):
    """
    Get comprehensive coding benchmark scores from all integrated sources
    
    Returns individual benchmark results from:
    - SWE-Bench Verified (35 models)
    - BigCode Models (172 models)  
    - EvalPlus (400 models)
    - And more...
    """
    try:
        db_path = "/app/src/db/meta_llm_leaderboard.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Base query for new coding_benchmarks table
        query = """
            SELECT 
                model_name,
                raw_model_name,
                benchmark_name,
                metric,
                score,
                source_url
            FROM coding_benchmarks
        """
        
        params = []
        if benchmark:
            query += " WHERE benchmark_name LIKE ?"
            params.append(f"%{benchmark}%")
            
        query += " ORDER BY score DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Group results by benchmark
        benchmarks = {}
        for row in results:
            benchmark_name = row['benchmark_name']
            if benchmark_name not in benchmarks:
                benchmarks[benchmark_name] = {
                    'name': benchmark_name,
                    'models': []
                }
            
            benchmarks[benchmark_name]['models'].append({
                'model_name': row['model_name'],
                'raw_model_name': row['raw_model_name'],
                'score': row['score'],
                'metric': row['metric'],
                'source_url': row['source_url']
            })
        
        # Limit results per benchmark and add metadata
        for benchmark_name, benchmark_data in benchmarks.items():
            benchmark_data['models'] = benchmark_data['models'][:limit]
            benchmark_data['total_models'] = len(benchmark_data['models'])
            
            # Add specific metadata per benchmark
            if benchmark_name == "SWE-Bench Verified":
                benchmark_data['description'] = "Real-world GitHub software engineering issue resolution"
                benchmark_data['metric_description'] = "Percentage of 500 verified issues resolved"
            elif benchmark_name == "BigCode Models":
                benchmark_data['description'] = "Comprehensive coding evaluation across multiple languages"
                benchmark_data['metric_description'] = "Pass@1 scores on various coding tasks"
            elif benchmark_name == "EvalPlus":
                benchmark_data['description'] = "Enhanced HumanEval+ and MBPP+ coding evaluation"
                benchmark_data['metric_description'] = "Pass@1 scores on base and plus test sets"
        
        conn.close()
        
        return {
            "total_benchmarks": len(benchmarks),
            "benchmarks": list(benchmarks.values()),
            "total_models": sum(len(b['models']) for b in benchmarks.values()),
            "generated_at": datetime.now().isoformat(),
            "note": "Comprehensive coding benchmark integration including SWE-Bench, BigCode, EvalPlus"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get coding benchmarks: {str(e)}")

@router.get("/coding/aider")
async def get_aider_leaderboard(limit: int = Query(50, ge=1, le=100)):
    """
    Get Aider.chat coding benchmark results specifically
    """
    try:
        conn = sqlite3.connect("meta_llm.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                rs.model_name,
                rs.value as score,
                rs.benchmark
            FROM raw_scores rs
            JOIN leaderboards l ON rs.leaderboard_id = l.id
            WHERE l.name = 'Aider.chat Code LB'
            ORDER BY rs.value DESC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        
        models = []
        for row in results:
            models.append({
                'model_name': row['model_name'],
                'score': row['score'],
                'benchmark': row['benchmark']
            })
        
        conn.close()
        
        return {
            "leaderboard": "Aider.chat Code LB",
            "benchmark": "Aider Polyglot Benchmark",
            "description": "Code editing performance across 6 programming languages (C++, Go, Java, JavaScript, Python, Rust)",
            "total_models": len(models),
            "models": models,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Aider leaderboard: {str(e)}")

@router.get("/coding/swe-bench")
async def get_swe_bench_leaderboard(limit: int = Query(50, ge=1, le=100)):
    """
    Get SWE-Bench Verified results specifically
    """
    try:
        db_path = "/app/src/db/meta_llm_leaderboard.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                model_name,
                raw_model_name,
                score,
                metric,
                source_url
            FROM coding_benchmarks
            WHERE benchmark_name = 'SWE-Bench Verified'
            ORDER BY score DESC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        
        models = []
        for row in results:
            models.append({
                'model_name': row['model_name'],
                'raw_model_name': row['raw_model_name'],
                'score': row['score'],
                'metric': row['metric'],
                'source_url': row['source_url']
            })
        
        conn.close()
        
        return {
            "leaderboard": "SWE-Bench Verified",
            "benchmark": "SWE-Bench",
            "description": "Real-world GitHub software engineering issue resolution",
            "metric_description": "Percentage of 500 human-verified solvable issues resolved",
            "total_models": len(models),
            "models": models,
            "website": "https://www.swebench.com/",
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get SWE-Bench leaderboard: {str(e)}")

@router.get("/coding/model/{model_name}")
async def get_model_coding_scores(model_name: str):
    """
    Get all coding benchmark scores for a specific model
    """
    try:
        conn = sqlite3.connect("meta_llm.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                rs.model_name,
                rs.value as score,
                rs.benchmark,
                l.name as leaderboard_name,
                l.category
            FROM raw_scores rs
            JOIN leaderboards l ON rs.leaderboard_id = l.id
            WHERE rs.model_name = ? AND l.category IN ('coding', 'software_engineering', 'programming')
            ORDER BY l.name, rs.value DESC
        """, (model_name,))
        
        results = cursor.fetchall()
        
        if not results:
            raise HTTPException(status_code=404, detail=f"No coding scores found for model: {model_name}")
        
        benchmarks = []
        for row in results:
            benchmarks.append({
                'leaderboard': row['leaderboard_name'],
                'benchmark': row['benchmark'],
                'score': row['score'],
                'category': row['category']
            })
        
        conn.close()
        
        return {
            "model_name": model_name,
            "total_benchmarks": len(benchmarks),
            "benchmarks": benchmarks,
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model scores: {str(e)}")