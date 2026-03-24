"""
Master Benchmark Registry - Canonical benchmark tracking system
Handles benchmark discovery, categorization, and metadata management
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, Float, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import re

Base = declarative_base()

class BenchmarkCategory(enum.Enum):
    """Standard benchmark categories for consistent classification"""
    CODE = "Code"
    REASONING = "Reasoning" 
    TRUTHFULNESS = "Truthfulness"
    LONG_CONTEXT = "LongContext"
    TOOL = "Tool"
    MULTILINGUAL = "Multilingual"
    DOMAIN_MED = "Domain-Med"
    DOMAIN_LAW = "Domain-Law"
    DOMAIN_FINANCE = "Domain-Finance"
    HUMAN_PREF = "HumanPref"
    MISC = "Misc"

class BenchmarkUnit(enum.Enum):
    """Standard units for benchmark measurements"""
    ACCURACY = "accuracy"
    ELO = "Elo"
    ERROR_RATE = "error-rate"
    SCORE = "score"
    PERCENTAGE = "percentage"
    BLEU = "BLEU"
    ROUGE = "ROUGE"
    PERPLEXITY = "perplexity"
    F1 = "f1"
    EXACT_MATCH = "exact_match"

class MasterBenchmark(Base):
    """
    Canonical benchmark registry - single source of truth for all benchmarks
    """
    __tablename__ = "master_benchmarks"
    
    # Primary identifier (kebab-case canonical name)
    benchmark_id = Column(String(255), primary_key=True)  # e.g., "human-eval"
    
    # Display information
    display_name = Column(String(255), nullable=False)  # e.g., "HumanEval"
    short_name = Column(String(100))  # e.g., "HE" for tables
    description = Column(Text)
    
    # Classification
    category = Column(Enum(BenchmarkCategory), nullable=False)
    subcategory = Column(String(100))  # e.g., "python-coding", "legal-reasoning"
    
    # Measurement details
    unit = Column(Enum(BenchmarkUnit), default=BenchmarkUnit.ACCURACY)
    higher_is_better = Column(Boolean, default=True)
    score_range_min = Column(Float)  # Known range for normalization
    score_range_max = Column(Float)
    
    # Weighting and importance
    default_weight = Column(Float, default=1.0)  # For composite calculations
    quality_tier = Column(String(20), default="standard")  # premium, standard, experimental
    
    # External references
    official_url = Column(Text)
    paper_url = Column(Text)
    github_url = Column(Text)
    
    # Registry metadata
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    auto_discovered = Column(Boolean, default=False)  # Found via automated discovery
    
    # Data source tracking
    source_leaderboards = Column(Text)  # JSON list of leaderboard sources
    
    # Relationships
    aliases = relationship("BenchmarkAlias", back_populates="benchmark")
    
    @staticmethod
    def canonicalize_name(raw_name: str) -> str:
        """
        Convert benchmark name to canonical kebab-case format
        Examples:
        - "HumanEval" -> "human-eval"
        - "MMLU (5-shot)" -> "mmlu-5-shot"
        - "GSM8K" -> "gsm8k"
        """
        # Convert to lowercase
        name = raw_name.lower()
        
        # Handle common patterns
        name = re.sub(r'\s*\([^)]*\)', '', name)  # Remove parenthetical info initially
        name = re.sub(r'[\s_]+', '-', name)  # Spaces/underscores to hyphens
        name = re.sub(r'[^a-z0-9\-]', '', name)  # Remove special chars
        name = re.sub(r'-+', '-', name)  # Collapse multiple hyphens
        name = name.strip('-')  # Remove leading/trailing hyphens
        
        return name
    
    @staticmethod
    def categorize_benchmark(name: str, description: str = "") -> BenchmarkCategory:
        """
        Auto-categorize benchmark based on name and description
        """
        name_lower = name.lower()
        desc_lower = description.lower()
        combined = f"{name_lower} {desc_lower}"
        
        # Code generation/repair
        if any(term in combined for term in [
            'humaneval', 'mbpp', 'codegen', 'code', 'programming', 'python', 
            'javascript', 'bigcode', 'evalplus', 'ds-1000'
        ]):
            return BenchmarkCategory.CODE
        
        # Truthfulness/factuality
        if any(term in combined for term in [
            'truthful', 'factual', 'hallucination', 'factcheck', 'verification'
        ]):
            return BenchmarkCategory.TRUTHFULNESS
        
        # Long context
        if any(term in combined for term in [
            'long', 'context', 'length', 'needle', 'haystack', 'longeval'
        ]):
            return BenchmarkCategory.LONG_CONTEXT
        
        # Tool use
        if any(term in combined for term in [
            'tool', 'function', 'api', 'berkeley', 'toolbench'
        ]):
            return BenchmarkCategory.TOOL
        
        # Medical domain
        if any(term in combined for term in [
            'medical', 'medqa', 'usmle', 'pubmed', 'clinical', 'biomedical'
        ]):
            return BenchmarkCategory.DOMAIN_MED
        
        # Legal domain  
        if any(term in combined for term in [
            'legal', 'law', 'bar', 'legalbench', 'jurisprudence'
        ]):
            return BenchmarkCategory.DOMAIN_LAW
        
        # Finance domain
        if any(term in combined for term in [
            'finance', 'financial', 'finqa', 'economics', 'accounting'
        ]):
            return BenchmarkCategory.DOMAIN_FINANCE
        
        # Human preference (usually Elo-based)
        if any(term in combined for term in [
            'arena', 'elo', 'preference', 'chatbot', 'lmsys', 'human-eval'
        ]) and 'elo' in combined:
            return BenchmarkCategory.HUMAN_PREF
        
        # Multilingual (check for non-English indicators)
        if any(term in combined for term in [
            'multilingual', 'chinese', 'c-eval', 'ceval', 'french', 'german',
            'mgsm', 'xnli', 'tydiqa', 'mlqa'
        ]):
            return BenchmarkCategory.MULTILINGUAL
        
        # Default to reasoning for academic benchmarks
        if any(term in combined for term in [
            'mmlu', 'hellaswag', 'arc', 'winogrande', 'reasoning', 'logic',
            'commonsense', 'natural', 'language'
        ]):
            return BenchmarkCategory.REASONING
        
        # Default fallback
        return BenchmarkCategory.MISC
    
    @classmethod
    def get_or_create(cls, session, raw_name: str, **kwargs):
        """
        Get existing benchmark or create new one with auto-categorization
        """
        canonical_id = cls.canonicalize_name(raw_name)
        
        # Try to find by canonical ID first
        benchmark = session.query(cls).filter_by(benchmark_id=canonical_id).first()
        
        if not benchmark:
            # Check if this might be an alias
            alias = session.query(BenchmarkAlias).filter_by(alias=raw_name.lower()).first()
            if alias:
                return alias.benchmark
        
        if not benchmark:
            # Auto-categorize if not provided
            if 'category' not in kwargs:
                kwargs['category'] = cls.categorize_benchmark(
                    raw_name, 
                    kwargs.get('description', '')
                )
            
            # Create new benchmark
            benchmark = cls(
                benchmark_id=canonical_id,
                display_name=kwargs.get('display_name', raw_name),
                auto_discovered=kwargs.get('auto_discovered', True),
                **kwargs
            )
            session.add(benchmark)
            session.flush()
        
        # Update last seen
        benchmark.last_updated = datetime.utcnow()
        
        # Add alias if different from canonical
        if raw_name.lower() != canonical_id:
            existing_alias = session.query(BenchmarkAlias).filter_by(
                benchmark_id=canonical_id, 
                alias=raw_name.lower()
            ).first()
            
            if not existing_alias:
                alias = BenchmarkAlias(
                    benchmark_id=canonical_id,
                    alias=raw_name.lower()
                )
                session.add(alias)
        
        return benchmark


class BenchmarkAlias(Base):
    """
    Benchmark alias tracking for name variations
    """
    __tablename__ = "benchmark_aliases"
    
    id = Column(Integer, primary_key=True)
    benchmark_id = Column(String(255), ForeignKey('master_benchmarks.benchmark_id'), nullable=False)
    alias = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    benchmark = relationship("MasterBenchmark", back_populates="aliases")


class BenchmarkRegistry:
    """
    Service class for benchmark registry operations
    """
    
    def __init__(self, session):
        self.session = session
    
    def register_benchmark(self, raw_name: str, **metadata) -> MasterBenchmark:
        """
        Register a benchmark with auto-categorization and deduplication
        """
        return MasterBenchmark.get_or_create(self.session, raw_name, **metadata)
    
    def update_benchmark_metadata(self, benchmark_id: str, **updates):
        """
        Update benchmark metadata (weights, URLs, etc.)
        """
        benchmark = self.session.query(MasterBenchmark).filter_by(
            benchmark_id=benchmark_id
        ).first()
        
        if benchmark:
            for key, value in updates.items():
                if hasattr(benchmark, key):
                    setattr(benchmark, key, value)
            benchmark.last_updated = datetime.utcnow()
            return benchmark
        return None
    
    def get_benchmarks_by_category(self, category: BenchmarkCategory) -> list:
        """
        Get all active benchmarks in a category
        """
        return self.session.query(MasterBenchmark).filter_by(
            category=category,
            is_active=True
        ).order_by(MasterBenchmark.default_weight.desc()).all()
    
    def get_category_weights(self) -> dict:
        """
        Get default weights for each category (for composite scoring)
        """
        weights = {}
        for category in BenchmarkCategory:
            benchmarks = self.get_benchmarks_by_category(category)
            if benchmarks:
                weights[category.value] = sum(b.default_weight for b in benchmarks)
        return weights
    
    def auto_discover_from_leaderboard(self, leaderboard_data: dict, source_name: str):
        """
        Auto-discover new benchmarks from leaderboard column headers
        """
        discovered = []
        
        # Extract column headers that look like benchmarks
        headers = leaderboard_data.get('headers', [])
        for header in headers:
            # Skip obvious non-benchmark columns
            if header.lower() in ['model', 'rank', 'score', 'average', 'overall']:
                continue
            
            # Check if we already know this benchmark
            existing = self.find_benchmark_by_name(header)
            if not existing:
                # Auto-register new benchmark
                benchmark = self.register_benchmark(
                    header,
                    auto_discovered=True,
                    source_leaderboards=f'["{source_name}"]',
                    description=f"Auto-discovered from {source_name}"
                )
                discovered.append(benchmark)
        
        return discovered
    
    def find_benchmark_by_name(self, name: str) -> MasterBenchmark:
        """
        Find benchmark by any known name or alias
        """
        canonical = MasterBenchmark.canonicalize_name(name)
        
        # Try canonical first
        benchmark = self.session.query(MasterBenchmark).filter_by(
            benchmark_id=canonical
        ).first()
        if benchmark:
            return benchmark
        
        # Try aliases
        alias = self.session.query(BenchmarkAlias).filter_by(
            alias=name.lower()
        ).first()
        if alias:
            return alias.benchmark
        
        return None
    
    def get_registry_statistics(self) -> dict:
        """
        Get benchmark registry statistics
        """
        from sqlalchemy import func
        
        total_benchmarks = self.session.query(func.count(MasterBenchmark.benchmark_id)).scalar()
        active_benchmarks = self.session.query(func.count(MasterBenchmark.benchmark_id)).filter_by(is_active=True).scalar()
        auto_discovered = self.session.query(func.count(MasterBenchmark.benchmark_id)).filter_by(auto_discovered=True).scalar()
        
        # Benchmarks by category
        category_counts = self.session.query(
            MasterBenchmark.category,
            func.count(MasterBenchmark.benchmark_id)
        ).filter_by(is_active=True).group_by(MasterBenchmark.category).all()
        
        return {
            "total_benchmarks": total_benchmarks,
            "active_benchmarks": active_benchmarks,
            "auto_discovered": auto_discovered,
            "manually_curated": active_benchmarks - auto_discovered,
            "category_distribution": {cat.value: count for cat, count in category_counts}
        }
    
    def validate_category_coverage(self) -> dict:
        """
        Ensure all categories have at least one benchmark
        """
        coverage = {}
        for category in BenchmarkCategory:
            benchmarks = self.get_benchmarks_by_category(category)
            coverage[category.value] = {
                "count": len(benchmarks),
                "has_coverage": len(benchmarks) > 0,
                "benchmarks": [b.benchmark_id for b in benchmarks[:5]]  # Sample
            }
        
        return coverage