from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, Text, ForeignKey, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Leaderboard(Base):
    __tablename__ = 'leaderboards'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, unique=True, nullable=False)
    category = Column(Text, nullable=False)
    # Add relationship to raw_scores if needed

class RawScore(Base):
    __tablename__ = 'raw_scores'
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(Text, nullable=False)
    leaderboard_id = Column(Integer, ForeignKey('leaderboards.id'), nullable=False)
    benchmark = Column(Text, nullable=False)
    metric = Column(Text, nullable=False)
    value = Column(Float, nullable=False)
    higher_is_better = Column(Boolean, nullable=False)
    scraped_at = Column(TIMESTAMP, nullable=False)
    __table_args__ = (
        UniqueConstraint('model_name', 'leaderboard_id', 'benchmark', 'scraped_at', name='uq_rawscore'),
    )

class NormalizedScore(Base):
    __tablename__ = 'normalized_scores'
    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_score_id = Column(Integer, ForeignKey('raw_scores.id'), nullable=False, unique=True)
    normalized_value = Column(Float, nullable=False)        # 0-100 normalized score
    confidence_score = Column(Float, nullable=False)        # 0-1 confidence in normalization
    normalization_method = Column(Text, nullable=False)     # Algorithm used
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to raw_scores
    raw_score = relationship("RawScore", backref="normalized_score") 