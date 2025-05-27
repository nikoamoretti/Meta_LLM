from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Model(Base):
    """LLM Model"""
    __tablename__ = 'models'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    organization = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    scores = relationship("Score", back_populates="model", cascade="all, delete-orphan")

class Benchmark(Base):
    """Benchmark/Metric definition"""
    __tablename__ = 'benchmarks'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)  # general, code, medical, etc.
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scores = relationship("Score", back_populates="benchmark", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('name', 'category', name='uq_benchmark_name_category'),
        Index('idx_benchmark_category', 'category'),
    )

class Score(Base):
    """Model scores on benchmarks"""
    __tablename__ = 'scores'
    
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    benchmark_id = Column(Integer, ForeignKey('benchmarks.id'), nullable=False)
    value = Column(Float, nullable=False)
    normalized_value = Column(Float)  # 0-100 normalized score
    source = Column(String(255))  # Which scraper/leaderboard this came from
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    model = relationship("Model", back_populates="scores")
    benchmark = relationship("Benchmark", back_populates="scores")
    
    __table_args__ = (
        UniqueConstraint('model_id', 'benchmark_id', name='uq_model_benchmark'),
        Index('idx_score_model', 'model_id'),
        Index('idx_score_benchmark', 'benchmark_id'),
        Index('idx_score_normalized', 'normalized_value'),
    ) 