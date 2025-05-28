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

# NEW: Normalized Scoring Models for Task 5.1

class CategoryScore(BaseModel):
    """Category score with confidence metrics"""
    normalized_score: float          # 0-100 normalized score
    confidence: float               # 0-1 confidence in normalization
    benchmark_count: int           # Number of benchmarks in category
    raw_score_avg: Optional[float] = None  # Average raw score for reference

class NormalizedModelScore(BaseModel):
    """Model score with advanced normalized scoring"""
    model: str
    overall_normalized: float       # 0-100 composite score
    overall_confidence: float       # 0-1 confidence
    global_rank: Optional[int] = None
    
    # Category scores with confidence
    category_scores: Dict[str, CategoryScore]
    
    # Quality indicators
    normalization_quality: str     # HIGH/MEDIUM/LOW
    benchmark_count: int
    last_updated: str

class DetailedScoreResponse(BaseModel):
    """Detailed score response with raw + normalized + confidence"""
    model: str
    overall_normalized: float
    overall_confidence: float
    global_rank: Optional[int] = None
    
    # Individual benchmark details
    benchmark_details: List[Dict[str, any]]  # name, raw_score, normalized_score, confidence, method
    
    # Category summaries
    category_summaries: Dict[str, CategoryScore]
    
    # Meta information
    total_benchmarks: int
    normalization_quality_score: float
    last_normalization_update: str

class NormalizationStats(BaseModel):
    """Platform-wide normalization statistics"""
    total_normalized_scores: int
    average_confidence: float
    confidence_range: Dict[str, float]  # min, max
    confidence_distribution: Dict[str, any]  # high/medium/low counts and percentages
    normalization_methods: Dict[str, int]  # method name -> count
    quality_indicators: Dict[str, any]

class ProcessingReportResponse(BaseModel):
    """Batch normalization processing report"""
    total_scores: int
    processed_scores: int
    failed_scores: int
    average_confidence: float
    processing_time: float
    success_rate: float
    errors: List[str]

# NEW: Composite Scoring Models for Task 5.2

class ScoringProfile(BaseModel):
    """Professional scoring profile configuration"""
    id: int
    name: str
    description: str
    weights: Dict[str, float]  # domain -> weight mapping

class CompositeModelScore(BaseModel):
    """Model with composite score for a specific profile"""
    model_name: str
    composite_score: float      # 0-100 weighted composite score
    confidence_score: float     # 0-1 confidence in composite calculation
    domain_coverage: int        # Number of domains with scores (0-6)
    profile_name: str

class DomainContribution(BaseModel):
    """Individual domain contribution to composite score"""
    domain_score: float         # 0-100 domain score
    confidence: float          # 0-1 confidence
    benchmark_count: int       # Benchmarks in this domain
    weight_in_profile: float   # Weight in current profile
    contribution: float        # domain_score * weight

class CompositeDetailResponse(BaseModel):
    """Detailed composite score breakdown for a model"""
    model_name: str
    profile_name: str
    composite_score: float
    confidence_score: float
    domain_coverage: str       # "4/6" format
    
    # Detailed breakdowns
    domain_breakdown: Dict[str, DomainContribution]
    missing_domains: List[str]
    profile_weights: Dict[str, float]
    
    # Methodology transparency
    methodology: Dict[str, any]

class CompositeLeaderboardResponse(BaseModel):
    """Composite leaderboard for a specific profile"""
    profile_name: str
    total_models: int
    generated_at: str
    leaderboard: List[CompositeModelScore]

class CompositeStatistics(BaseModel):
    """Composite scoring system statistics"""
    generated_at: str
    system_overview: Dict[str, any]
    profile_statistics: List[Dict[str, any]]
    methodology: Dict[str, str]

class ProfileComparisonResponse(BaseModel):
    """Model ranking comparison across profiles"""
    total_models: int
    profiles_compared: List[str]
    comparison: List[Dict[str, any]]  # model_name + scores per profile
    note: str 