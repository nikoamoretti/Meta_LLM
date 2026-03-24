"""Add model aliases table for name normalization

Revision ID: 003
Revises: 002
Create Date: 2025-06-28

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade():
    """Create model_aliases table for handling model name variations"""
    
    # Create model_aliases table
    op.create_table('model_aliases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('canonical_name', sa.Text(), nullable=False),
        sa.Column('alias', sa.Text(), nullable=False),
        sa.Column('source', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('idx_model_aliases_alias', 'model_aliases', ['alias'], unique=True)
    op.create_index('idx_model_aliases_canonical', 'model_aliases', ['canonical_name'])
    op.create_index('idx_model_aliases_alias_lower', 'model_aliases', [sa.text('LOWER(alias)')])
    
    # Create canonical_models table to store official model names
    op.create_table('canonical_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('canonical_name', sa.Text(), nullable=False),
        sa.Column('model_family', sa.Text(), nullable=True),
        sa.Column('organization', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_canonical_models_name', 'canonical_models', ['canonical_name'], unique=True)
    
    # Add initial critical aliases for known issues
    op.execute("""
        INSERT INTO canonical_models (canonical_name, model_family, organization) VALUES
        ('GPT 4.1', 'GPT', 'OpenAI'),
        ('GPT-4', 'GPT', 'OpenAI'),
        ('GPT-4o', 'GPT', 'OpenAI'),
        ('Claude 4 Opus', 'Claude', 'Anthropic'),
        ('Claude 4 Sonnet', 'Claude', 'Anthropic'),
        ('Claude 3.5 Sonnet', 'Claude', 'Anthropic'),
        ('o3', 'o-series', 'OpenAI'),
        ('o3-mini', 'o-series', 'OpenAI')
    """)
    
    # Insert initial aliases for GPT models
    op.execute("""
        INSERT INTO model_aliases (canonical_name, alias, source, confidence_score) VALUES
        -- GPT 4.1 aliases
        ('GPT 4.1', 'gpt-4.1', 'aider.chat', 1.0),
        ('GPT 4.1', 'GPT-4.1', 'common', 1.0),
        ('GPT 4.1', 'gpt 4.1', 'common', 1.0),
        ('GPT 4.1', 'GPT4.1', 'common', 0.95),
        ('GPT 4.1', 'gpt4.1', 'common', 0.95),
        
        -- GPT-4 aliases (different from GPT 4.1!)
        ('GPT-4', 'gpt-4', 'common', 1.0),
        ('GPT-4', 'GPT 4', 'common', 1.0),
        ('GPT-4', 'gpt 4', 'common', 1.0),
        ('GPT-4', 'GPT4', 'common', 0.95),
        
        -- GPT-4o aliases
        ('GPT-4o', 'gpt-4o', 'common', 1.0),
        ('GPT-4o', 'GPT 4o', 'common', 1.0),
        ('GPT-4o', 'gpt 4o', 'common', 1.0),
        ('GPT-4o', 'chatgpt-4o-latest', 'aider.chat', 1.0)
    """)
    
    # Insert Claude aliases
    op.execute("""
        INSERT INTO model_aliases (canonical_name, alias, source, confidence_score) VALUES
        -- Claude 4 Opus
        ('Claude 4 Opus', 'claude-opus-4', 'common', 1.0),
        ('Claude 4 Opus', 'Claude-4-Opus', 'common', 1.0),
        ('Claude 4 Opus', 'claude 4 opus', 'common', 1.0),
        ('Claude 4 Opus', 'claude-opus-4-20250514', 'aider.chat', 1.0),
        ('Claude 4 Opus', 'claude-opus-4-20250514 (32k thinking)', 'aider.chat', 1.0),
        ('Claude 4 Opus', 'claude-opus-4-20250514 (no think)', 'aider.chat', 1.0),
        
        -- Claude 4 Sonnet
        ('Claude 4 Sonnet', 'claude-sonnet-4', 'common', 1.0),
        ('Claude 4 Sonnet', 'Claude-4-Sonnet', 'common', 1.0),
        ('Claude 4 Sonnet', 'claude 4 sonnet', 'common', 1.0),
        ('Claude 4 Sonnet', 'claude-sonnet-4-20250514', 'aider.chat', 1.0),
        ('Claude 4 Sonnet', 'claude-sonnet-4-20250514 (32k thinking)', 'aider.chat', 1.0),
        
        -- Claude 3.5 Sonnet
        ('Claude 3.5 Sonnet', 'claude-3-5-sonnet', 'common', 1.0),
        ('Claude 3.5 Sonnet', 'Claude-3.5-Sonnet', 'common', 1.0),
        ('Claude 3.5 Sonnet', 'claude 3.5 sonnet', 'common', 1.0),
        ('Claude 3.5 Sonnet', 'claude-3-5-sonnet-20241022', 'common', 1.0)
    """)
    
    # Insert o3 aliases
    op.execute("""
        INSERT INTO model_aliases (canonical_name, alias, source, confidence_score) VALUES
        -- o3 aliases
        ('o3', 'o3-high', 'common', 1.0),
        ('o3', 'o3 high', 'common', 1.0),
        ('o3', 'O3', 'common', 1.0),
        ('o3', 'o3 (high)', 'aider.chat', 1.0),
        
        -- o3-mini aliases
        ('o3-mini', 'o3 mini', 'common', 1.0),
        ('o3-mini', 'O3-mini', 'common', 1.0),
        ('o3-mini', 'o3-mini (high)', 'aider.chat', 1.0)
    """)

def downgrade():
    """Remove model alias tables"""
    op.drop_index('idx_model_aliases_alias_lower', table_name='model_aliases')
    op.drop_index('idx_model_aliases_canonical', table_name='model_aliases')
    op.drop_index('idx_model_aliases_alias', table_name='model_aliases')
    op.drop_table('model_aliases')
    
    op.drop_index('idx_canonical_models_name', table_name='canonical_models')
    op.drop_table('canonical_models')