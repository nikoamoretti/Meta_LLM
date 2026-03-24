"""add model aliases table

Revision ID: 002
Revises: 001
Create Date: 2025-06-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create model_aliases table
    op.create_table('model_aliases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('canonical_name', sa.Text(), nullable=False),
        sa.Column('alias_name', sa.Text(), nullable=False),
        sa.Column('model_family', sa.Text(), nullable=False),
        sa.Column('version', sa.Text(), nullable=True),
        sa.Column('provider', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('alias_name', name='uq_alias_name')
    )
    
    # Create indexes for performance
    op.create_index('idx_model_aliases_canonical', 'model_aliases', ['canonical_name'])
    op.create_index('idx_model_aliases_family', 'model_aliases', ['model_family'])


def downgrade():
    op.drop_index('idx_model_aliases_family', table_name='model_aliases')
    op.drop_index('idx_model_aliases_canonical', table_name='model_aliases')
    op.drop_table('model_aliases')