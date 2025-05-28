from pydantic import BaseModel
from typing import Optional, List, Dict

class ModelScore(BaseModel):
    model: str
    overall: float
    global_rank: Optional[int] = None  # NEW: Global ranking position
    
    # Core categories
    code: Optional[float] = None
    hallucination: Optional[float] = None
    medical: Optional[float] = None
    legal: Optional[float] = None
    multilingual: Optional[float] = None
    reasoning: Optional[float] = None
    comprehensive: Optional[float] = None
    
    # NEW: Extended categories
    chinese: Optional[float] = None
    emotional: Optional[float] = None
    instruction: Optional[float] = None
    finance: Optional[float] = None
    general: Optional[float] = None
    
    # Meta information
    benchmark_count: int
    # Add detailed benchmark breakdowns
    code_benchmarks: Optional[Dict[str, float]] = None
    medical_benchmarks: Optional[Dict[str, float]] = None
    legal_benchmarks: Optional[Dict[str, float]] = None
    # Add more as needed

class ModelDetailResponse(BaseModel):
    model: str
    overall: float
    global_rank: Optional[int] = None
    
    # Core categories
    code: Optional[float] = None
    hallucination: Optional[float] = None
    medical: Optional[float] = None
    legal: Optional[float] = None
    multilingual: Optional[float] = None
    reasoning: Optional[float] = None
    comprehensive: Optional[float] = None
    
    # NEW: Extended categories  
    chinese: Optional[float] = None
    emotional: Optional[float] = None
    instruction: Optional[float] = None
    finance: Optional[float] = None
    general: Optional[float] = None
    
    benchmarks: List[dict]
    history: List[dict]
    benchmark_count: Optional[int] = None 