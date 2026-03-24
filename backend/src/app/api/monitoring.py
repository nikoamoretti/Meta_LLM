"""
Monitoring API for Meta-LLM Platform
Provides real-time status and health monitoring for scraping and normalization systems
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
import logging
import sqlite3
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

try:
    from services.automated_normalization_service import AutomatedNormalizationService
    from services.composite_scoring_service import CompositeScoringService
except ImportError:
    AutomatedNormalizationService = None
    CompositeScoringService = None

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'meta_llm.db')
normalization_service = AutomatedNormalizationService(db_path) if AutomatedNormalizationService else None
composite_service = CompositeScoringService(db_path) if CompositeScoringService else None

@router.get("/monitoring/health")
async def get_system_health():
    """Get overall system health status"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Database connectivity check
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        
        # Basic data counts
        cursor.execute("SELECT COUNT(*) FROM raw_scores")
        total_scores = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT model_name) FROM raw_scores")
        total_models = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM composite_scores")
        composite_scores = cursor.fetchone()[0]
        
        # Recent data check (last 24 hours)
        yesterday = datetime.now() - timedelta(hours=24)
        cursor.execute("SELECT COUNT(*) FROM raw_scores WHERE scraped_at > ?", (yesterday,))
        recent_scores = cursor.fetchone()[0]
        
        # Normalization status
        normalization_stats = {}
        if normalization_service:
            normalization_stats = normalization_service.get_normalization_statistics()
        
        conn.close()
        
        # Health score calculation
        health_score = 100
        issues = []
        
        if total_scores == 0:
            health_score -= 50
            issues.append("No raw scores in database")
        
        if composite_scores == 0:
            health_score -= 30
            issues.append("No composite scores calculated")
        
        if recent_scores == 0:
            health_score -= 20
            issues.append("No data scraped in last 24 hours")
        
        if normalization_stats.get('coverage_percentage', 0) < 80:
            health_score -= 10
            issues.append("Model name normalization coverage below 80%")
        
        status = "healthy" if health_score >= 80 else "warning" if health_score >= 60 else "critical"
        
        return {
            "status": "success",
            "data": {
                "overall_health": {
                    "score": max(0, health_score),
                    "status": status,
                    "issues": issues,
                    "last_check": datetime.now().isoformat()
                },
                "database": {
                    "tables": table_count,
                    "total_scores": total_scores,
                    "total_models": total_models,
                    "composite_scores": composite_scores,
                    "recent_scores_24h": recent_scores
                },
                "normalization": normalization_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitoring/scraping-status")
async def get_scraping_status():
    """Get status of data scraping operations"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get leaderboard update times
        cursor.execute("""
            SELECT 
                l.name,
                l.category,
                COUNT(rs.id) as score_count,
                COUNT(DISTINCT rs.model_name) as model_count,
                MAX(rs.scraped_at) as last_update,
                MIN(rs.scraped_at) as first_update
            FROM leaderboards l
            LEFT JOIN raw_scores rs ON l.id = rs.leaderboard_id
            GROUP BY l.id, l.name, l.category
            ORDER BY last_update DESC
        """)
        
        leaderboards = []
        for row in cursor.fetchall():
            last_update = row['last_update']
            hours_since = None
            status = "unknown"
            
            if last_update:
                last_update_dt = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                hours_since = (datetime.now() - last_update_dt).total_seconds() / 3600
                
                if hours_since <= 24:
                    status = "current"
                elif hours_since <= 72:
                    status = "stale"
                else:
                    status = "outdated"
            
            leaderboards.append({
                "name": row['name'],
                "category": row['category'],
                "score_count": row['score_count'],
                "model_count": row['model_count'],
                "last_update": last_update,
                "first_update": row['first_update'],
                "hours_since_update": round(hours_since, 1) if hours_since else None,
                "status": status
            })
        
        # Overall scraping statistics
        current_sources = len([lb for lb in leaderboards if lb['status'] == 'current'])
        stale_sources = len([lb for lb in leaderboards if lb['status'] == 'stale'])
        outdated_sources = len([lb for lb in leaderboards if lb['status'] == 'outdated'])
        
        conn.close()
        
        return {
            "status": "success",
            "data": {
                "summary": {
                    "total_sources": len(leaderboards),
                    "current_sources": current_sources,
                    "stale_sources": stale_sources,
                    "outdated_sources": outdated_sources,
                    "last_check": datetime.now().isoformat()
                },
                "leaderboards": leaderboards
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting scraping status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitoring/data-freshness")
async def get_data_freshness():
    """Get data freshness metrics by category"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Data freshness by category
        cursor.execute("""
            SELECT 
                l.category,
                COUNT(DISTINCT l.id) as source_count,
                COUNT(DISTINCT rs.model_name) as model_count,
                COUNT(rs.id) as score_count,
                MAX(rs.scraped_at) as latest_update,
                MIN(rs.scraped_at) as earliest_update,
                AVG(julianday('now') - julianday(rs.scraped_at)) as avg_age_days
            FROM leaderboards l
            LEFT JOIN raw_scores rs ON l.id = rs.leaderboard_id
            GROUP BY l.category
            ORDER BY latest_update DESC
        """)
        
        categories = []
        for row in cursor.fetchall():
            latest = row['latest_update']
            status = "unknown"
            hours_since = None
            
            if latest:
                latest_dt = datetime.fromisoformat(latest.replace('Z', '+00:00'))
                hours_since = (datetime.now() - latest_dt).total_seconds() / 3600
                
                if hours_since <= 24:
                    status = "fresh"
                elif hours_since <= 72:
                    status = "moderate"
                else:
                    status = "stale"
            
            categories.append({
                "category": row['category'],
                "source_count": row['source_count'],
                "model_count": row['model_count'],
                "score_count": row['score_count'],
                "latest_update": latest,
                "earliest_update": row['earliest_update'],
                "avg_age_days": round(row['avg_age_days'] or 0, 1),
                "hours_since_update": round(hours_since, 1) if hours_since else None,
                "freshness_status": status
            })
        
        conn.close()
        
        return {
            "status": "success",
            "data": {
                "categories": categories,
                "last_check": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting data freshness: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitoring/composite-scores")
async def get_composite_scores_status():
    """Get composite scoring system status"""
    try:
        if not composite_service:
            raise HTTPException(status_code=503, detail="Composite scoring service not available")
        
        stats = composite_service.get_composite_statistics()
        
        # Calculate freshness of composite scores
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT MAX(updated_at) FROM composite_scores")
        last_update = cursor.fetchone()[0]
        
        conn.close()
        
        hours_since_update = None
        if last_update:
            last_update_dt = datetime.fromisoformat(last_update)
            hours_since_update = (datetime.now() - last_update_dt).total_seconds() / 3600
        
        return {
            "status": "success",
            "data": {
                "statistics": stats,
                "last_update": last_update,
                "hours_since_update": round(hours_since_update, 1) if hours_since_update else None,
                "last_check": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting composite scores status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitoring/alerts")
async def get_system_alerts():
    """Get current system alerts and warnings"""
    try:
        alerts = []
        warnings = []
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check for outdated data sources
        cursor.execute("""
            SELECT l.name, MAX(rs.scraped_at) as last_update
            FROM leaderboards l
            LEFT JOIN raw_scores rs ON l.id = rs.leaderboard_id
            GROUP BY l.id, l.name
            HAVING last_update IS NULL OR 
                   julianday('now') - julianday(last_update) > 3
        """)
        
        for row in cursor.fetchall():
            if row[1] is None:
                alerts.append(f"No data for source: {row[0]}")
            else:
                days_old = (datetime.now() - datetime.fromisoformat(row[1])).days
                alerts.append(f"Source '{row[0]}' data is {days_old} days old")
        
        # Check composite score freshness
        cursor.execute("SELECT MAX(updated_at) FROM composite_scores")
        last_composite = cursor.fetchone()[0]
        
        if last_composite:
            hours_old = (datetime.now() - datetime.fromisoformat(last_composite)).total_seconds() / 3600
            if hours_old > 48:
                warnings.append(f"Composite scores are {hours_old:.1f} hours old")
        else:
            alerts.append("No composite scores found")
        
        # Check normalization coverage
        if normalization_service:
            stats = normalization_service.get_normalization_statistics()
            coverage = stats.get('coverage_percentage', 0)
            if coverage < 50:
                alerts.append(f"Low model normalization coverage: {coverage}%")
            elif coverage < 80:
                warnings.append(f"Model normalization coverage below target: {coverage}%")
        
        conn.close()
        
        return {
            "status": "success",
            "data": {
                "alerts": alerts,
                "warnings": warnings,
                "alert_count": len(alerts),
                "warning_count": len(warnings),
                "last_check": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitoring/dashboard")
async def get_monitoring_dashboard():
    """Get comprehensive monitoring dashboard data"""
    try:
        # Combine all monitoring data into one response
        health_response = await get_system_health()
        scraping_response = await get_scraping_status()
        freshness_response = await get_data_freshness()
        alerts_response = await get_system_alerts()
        
        composite_status = {}
        try:
            composite_response = await get_composite_scores_status()
            composite_status = composite_response["data"]
        except:
            composite_status = {"error": "Composite scoring service unavailable"}
        
        return {
            "status": "success",
            "data": {
                "health": health_response["data"],
                "scraping": scraping_response["data"],
                "freshness": freshness_response["data"],
                "composite_scores": composite_status,
                "alerts": alerts_response["data"],
                "generated_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating monitoring dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))