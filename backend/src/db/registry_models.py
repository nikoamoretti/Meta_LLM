"""
Master Model Registry - Canonical model tracking system
Handles model registration, aliasing, and lifecycle management across all sources
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import re

Base = declarative_base()

class MasterModel(Base):
    """
    Canonical model registry - single source of truth for all models
    """
    __tablename__ = "master_models"
    
    # Primary identifier (kebab-case canonical name)
    model_id = Column(String(255), primary_key=True)  # e.g., "gpt-4-turbo-preview"
    
    # Display information
    display_name = Column(String(255), nullable=False)  # e.g., "GPT-4 Turbo Preview"
    provider = Column(String(100))  # e.g., "OpenAI", "Anthropic", "Meta"
    
    # Technical specifications
    license = Column(String(100))  # e.g., "proprietary", "apache-2.0", "mit"
    params_b = Column(Float)  # Parameters in billions
    context_window = Column(Integer)  # Max context length
    
    # Registry metadata
    source_tag = Column(String(50), nullable=False)  # First discovered source
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # External links
    huggingface_id = Column(String(255))  # HF model identifier
    official_url = Column(Text)
    documentation_url = Column(Text)
    
    # Relationships
    aliases = relationship("ModelAlias", back_populates="model")
    scores = relationship("RawScore", back_populates="model")
    
    @staticmethod
    def canonicalize_name(raw_name: str) -> str:
        """
        Convert any model name to canonical kebab-case format
        Examples:
        - "GPT-4 Turbo Preview" -> "gpt-4-turbo-preview"
        - "claude-3-opus-20240229" -> "claude-3-opus-20240229"
        - "Meta-Llama-3-8B" -> "meta-llama-3-8b"
        """
        # Convert to lowercase
        name = raw_name.lower()
        
        # Replace spaces, underscores, and multiple hyphens with single hyphen
        name = re.sub(r'[\s_]+', '-', name)
        name = re.sub(r'-+', '-', name)
        
        # Remove special characters except hyphens and alphanumeric
        name = re.sub(r'[^a-z0-9\-]', '', name)
        
        # Remove trailing hash/version suffixes that are just noise
        name = re.sub(r'-v?\d*$', '', name)
        
        # Strip leading/trailing hyphens
        name = name.strip('-')
        
        return name
    
    @classmethod
    def get_or_create(cls, session, raw_name: str, source_tag: str, **kwargs):
        """
        Get existing model or create new one with proper aliasing
        """
        canonical_id = cls.canonicalize_name(raw_name)
        
        # Try to find by canonical ID first
        model = session.query(cls).filter_by(model_id=canonical_id).first()
        
        if not model:
            # Check if this might be an alias
            alias = session.query(ModelAlias).filter_by(alias=raw_name.lower()).first()
            if alias:
                model = alias.model
                model.last_seen = datetime.utcnow()
                return model
        
        if not model:
            # Create new model
            model = cls(
                model_id=canonical_id,
                display_name=kwargs.get('display_name', raw_name),
                source_tag=source_tag,
                **kwargs
            )
            session.add(model)
            session.flush()  # Get the ID
        
        # Always update last_seen
        model.last_seen = datetime.utcnow()
        
        # Add alias if different from canonical
        if raw_name.lower() != canonical_id:
            existing_alias = session.query(ModelAlias).filter_by(
                model_id=canonical_id, 
                alias=raw_name.lower()
            ).first()
            
            if not existing_alias:
                alias = ModelAlias(
                    model_id=canonical_id,
                    alias=raw_name.lower(),
                    source_tag=source_tag
                )
                session.add(alias)
        
        return model


class ModelAlias(Base):
    """
    Model alias tracking for name variations and collisions
    """
    __tablename__ = "model_aliases"
    
    id = Column(Integer, primary_key=True)
    model_id = Column(String(255), ForeignKey('master_models.model_id'), nullable=False)
    alias = Column(String(255), nullable=False, index=True)
    source_tag = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    model = relationship("MasterModel", back_populates="aliases")
    
    __table_args__ = (
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )


class ModelSourceTracking(Base):
    """
    Track which sources have seen which models for deprecation logic
    """
    __tablename__ = "model_source_tracking"
    
    id = Column(Integer, primary_key=True)
    model_id = Column(String(255), ForeignKey('master_models.model_id'), nullable=False)
    source_tag = Column(String(50), nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_present = Column(Boolean, default=True)
    
    # Unique constraint on model + source
    __table_args__ = (
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )


class ModelRegistry:
    """
    Service class for model registry operations
    """
    
    def __init__(self, session):
        self.session = session
    
    def register_model(self, raw_name: str, source_tag: str, **metadata) -> MasterModel:
        """
        Register a model from any source with proper deduplication
        """
        model = MasterModel.get_or_create(
            self.session, 
            raw_name, 
            source_tag, 
            **metadata
        )
        
        # Update source tracking
        self.update_source_tracking(model.model_id, source_tag)
        
        return model
    
    def update_source_tracking(self, model_id: str, source_tag: str):
        """
        Update that a source has seen this model recently
        """
        tracking = self.session.query(ModelSourceTracking).filter_by(
            model_id=model_id,
            source_tag=source_tag
        ).first()
        
        if not tracking:
            tracking = ModelSourceTracking(
                model_id=model_id,
                source_tag=source_tag
            )
            self.session.add(tracking)
        else:
            tracking.last_seen = datetime.utcnow()
            tracking.is_present = True
    
    def mark_model_absent(self, model_id: str, source_tag: str):
        """
        Mark that a model is no longer present in a source
        """
        tracking = self.session.query(ModelSourceTracking).filter_by(
            model_id=model_id,
            source_tag=source_tag
        ).first()
        
        if tracking:
            tracking.is_present = False
            tracking.last_seen = datetime.utcnow()
    
    def check_deprecations(self) -> list:
        """
        Find models that should be deprecated (absent from all sources for 180+ days)
        """
        from sqlalchemy import func, and_
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=180)
        
        # Models that haven't been seen in any source for 180+ days
        # AND have fewer than 5 scores
        candidates = self.session.query(MasterModel).filter(
            and_(
                MasterModel.last_seen < cutoff_date,
                MasterModel.is_active == True
            )
        ).all()
        
        deprecated = []
        for model in candidates:
            # Check if model has < 5 scores
            score_count = self.session.query(func.count(RawScore.id)).filter_by(
                model_name=model.model_id
            ).scalar()
            
            if score_count < 5:
                model.is_active = False
                deprecated.append(model.model_id)
        
        return deprecated
    
    def get_model_statistics(self) -> dict:
        """
        Get registry statistics for monitoring
        """
        total_models = self.session.query(func.count(MasterModel.model_id)).scalar()
        active_models = self.session.query(func.count(MasterModel.model_id)).filter_by(is_active=True).scalar()
        total_aliases = self.session.query(func.count(ModelAlias.id)).scalar()
        
        # Models by source
        source_counts = self.session.query(
            MasterModel.source_tag,
            func.count(MasterModel.model_id)
        ).group_by(MasterModel.source_tag).all()
        
        return {
            "total_models": total_models,
            "active_models": active_models,
            "deprecated_models": total_models - active_models,
            "total_aliases": total_aliases,
            "source_distribution": dict(source_counts)
        }
    
    def find_model_by_name(self, name: str) -> MasterModel:
        """
        Find model by any known name or alias
        """
        canonical = MasterModel.canonicalize_name(name)
        
        # Try canonical first
        model = self.session.query(MasterModel).filter_by(model_id=canonical).first()
        if model:
            return model
        
        # Try aliases
        alias = self.session.query(ModelAlias).filter_by(alias=name.lower()).first()
        if alias:
            return alias.model
        
        return None