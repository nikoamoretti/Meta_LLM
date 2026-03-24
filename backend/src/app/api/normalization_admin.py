"""
Admin API for Model Name Normalization
Provides endpoints for manual review and management of model aliases
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from services.automated_normalization_service import AutomatedNormalizationService
from services.model_name_normalizer import ModelNameNormalizer

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models for request/response
class AliasCreationRequest(BaseModel):
    original_name: str
    canonical_name: str
    model_family: str
    provider: Optional[str] = None

class SuggestionReviewRequest(BaseModel):
    original_name: str
    action: str  # 'approve' or 'reject'
    canonical_name: Optional[str] = None
    reviewer: Optional[str] = 'admin'

class NormalizationTestRequest(BaseModel):
    model_name: str

# Initialize services
normalization_service = AutomatedNormalizationService()
normalizer = ModelNameNormalizer()

@router.get("/normalization/status")
async def get_normalization_status():
    """Get current normalization system status"""
    try:
        stats = normalization_service.get_normalization_statistics()
        return {"status": "success", "data": stats}
    except Exception as e:
        logger.error(f"Error getting normalization status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/normalization/report")
async def get_normalization_report():
    """Get detailed normalization report"""
    try:
        report = normalizer.get_normalization_report()
        return {"status": "success", "data": report}
    except Exception as e:
        logger.error(f"Error getting normalization report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/normalization/suggestions")
async def get_normalization_suggestions(
    limit: int = Query(default=50, ge=1, le=200),
    confidence_min: float = Query(default=0.3, ge=0.0, le=1.0)
):
    """Get suggested model name normalizations for review"""
    try:
        suggestions = normalizer.get_suggested_aliases(limit=limit)
        
        # Filter by confidence
        filtered_suggestions = [
            s for s in suggestions 
            if s['confidence'] >= confidence_min
        ]
        
        return {
            "status": "success",
            "data": {
                "suggestions": filtered_suggestions,
                "total_count": len(filtered_suggestions),
                "confidence_filter": confidence_min
            }
        }
    except Exception as e:
        logger.error(f"Error getting normalization suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/normalization/review-queue")
async def get_review_queue(
    limit: int = Query(default=50, ge=1, le=200),
    status: str = Query(default="pending")
):
    """Get models in the manual review queue"""
    try:
        queue = normalization_service.get_review_queue(limit=limit, status=status)
        return {
            "status": "success",
            "data": {
                "queue": queue,
                "count": len(queue),
                "filter_status": status
            }
        }
    except Exception as e:
        logger.error(f"Error getting review queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/normalization/test")
async def test_normalization(request: NormalizationTestRequest):
    """Test normalization for a specific model name"""
    try:
        match = normalizer.normalize_model_name(request.model_name)
        
        return {
            "status": "success",
            "data": {
                "original_name": match.original_name,
                "canonical_name": match.canonical_name,
                "confidence": match.confidence,
                "match_type": match.match_type,
                "reasoning": match.reasoning
            }
        }
    except Exception as e:
        logger.error(f"Error testing normalization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/normalization/create-alias")
async def create_alias(request: AliasCreationRequest):
    """Manually create a new model alias"""
    try:
        import sqlite3
        
        conn = sqlite3.connect(normalization_service.db_path)
        cursor = conn.cursor()
        
        # Insert new alias
        cursor.execute("""
            INSERT OR IGNORE INTO model_aliases
            (canonical_name, alias_name, model_family, provider)
            VALUES (?, ?, ?, ?)
        """, (
            request.canonical_name,
            request.original_name,
            request.model_family,
            request.provider
        ))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            logger.info(f"Manual alias created: {request.original_name} -> {request.canonical_name}")
            return {
                "status": "success",
                "message": f"Alias created successfully",
                "data": {
                    "original_name": request.original_name,
                    "canonical_name": request.canonical_name
                }
            }
        else:
            return {
                "status": "warning",
                "message": "Alias already exists",
                "data": {
                    "original_name": request.original_name,
                    "canonical_name": request.canonical_name
                }
            }
        
    except Exception as e:
        logger.error(f"Error creating alias: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/normalization/review")
async def review_suggestion(request: SuggestionReviewRequest):
    """Approve or reject a normalization suggestion"""
    try:
        if request.action == "approve":
            canonical_name = request.canonical_name or request.original_name
            success = normalization_service.approve_suggestion(
                request.original_name,
                canonical_name,
                request.reviewer
            )
            
            if success:
                return {
                    "status": "success",
                    "message": f"Suggestion approved: {request.original_name} -> {canonical_name}",
                    "data": {
                        "action": "approved",
                        "original_name": request.original_name,
                        "canonical_name": canonical_name
                    }
                }
            else:
                raise HTTPException(status_code=400, detail="Failed to approve suggestion")
                
        elif request.action == "reject":
            success = normalization_service.reject_suggestion(
                request.original_name,
                request.reviewer
            )
            
            if success:
                return {
                    "status": "success",
                    "message": f"Suggestion rejected: {request.original_name}",
                    "data": {
                        "action": "rejected",
                        "original_name": request.original_name
                    }
                }
            else:
                raise HTTPException(status_code=400, detail="Failed to reject suggestion")
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")
        
    except Exception as e:
        logger.error(f"Error reviewing suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/normalization/auto-create")
async def auto_create_aliases(
    min_confidence: float = Query(default=0.9, ge=0.7, le=1.0)
):
    """Automatically create aliases for high-confidence matches"""
    try:
        created_count = normalizer.auto_create_high_confidence_aliases(min_confidence)
        
        return {
            "status": "success",
            "message": f"Auto-created {created_count} aliases with confidence >= {min_confidence}",
            "data": {
                "created_count": created_count,
                "min_confidence": min_confidence
            }
        }
    except Exception as e:
        logger.error(f"Error auto-creating aliases: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/normalization/run-daily")
async def run_daily_normalization():
    """Trigger daily normalization process"""
    try:
        report = normalization_service.run_daily_normalization()
        return {"status": "success", "data": report}
    except Exception as e:
        logger.error(f"Error running daily normalization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/normalization/families")
async def get_model_families():
    """Get all canonical model families and their aliases"""
    try:
        import sqlite3
        
        conn = sqlite3.connect(normalization_service.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                canonical_name,
                model_family,
                provider,
                COUNT(*) as alias_count,
                GROUP_CONCAT(alias_name, ', ') as aliases
            FROM model_aliases
            GROUP BY canonical_name, model_family, provider
            ORDER BY model_family, canonical_name
        """)
        
        families = {}
        for row in cursor.fetchall():
            family = row['model_family']
            if family not in families:
                families[family] = []
            
            families[family].append({
                'canonical_name': row['canonical_name'],
                'provider': row['provider'],
                'alias_count': row['alias_count'],
                'aliases': row['aliases'].split(', ') if row['aliases'] else []
            })
        
        conn.close()
        
        return {
            "status": "success",
            "data": {
                "families": families,
                "family_count": len(families),
                "total_canonical_models": sum(len(models) for models in families.values())
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting model families: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/normalization/alias/{alias_name}")
async def delete_alias(alias_name: str):
    """Delete a model alias"""
    try:
        import sqlite3
        
        conn = sqlite3.connect(normalization_service.db_path)
        cursor = conn.cursor()
        
        # Don't allow deleting canonical names (where alias_name = canonical_name)
        cursor.execute("""
            SELECT canonical_name FROM model_aliases 
            WHERE alias_name = ? AND alias_name = canonical_name
        """, (alias_name,))
        
        if cursor.fetchone():
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete canonical name. Delete all aliases first."
            )
        
        # Delete the alias
        cursor.execute("DELETE FROM model_aliases WHERE alias_name = ?", (alias_name,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        if deleted:
            return {
                "status": "success",
                "message": f"Alias '{alias_name}' deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Alias not found")
        
    except Exception as e:
        logger.error(f"Error deleting alias: {e}")
        raise HTTPException(status_code=500, detail=str(e))