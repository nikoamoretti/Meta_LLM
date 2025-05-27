"""initial tables

Revision ID: 001
Revises: 
Create Date: 2025-05-19 01:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create leaderboards table
    op.create_table('leaderboards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('category', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create raw_scores table
    op.create_table('raw_scores',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('model_name', sa.Text(), nullable=False),
        sa.Column('leaderboard_id', sa.Integer(), nullable=False),
        sa.Column('benchmark', sa.Text(), nullable=False),
        sa.Column('metric', sa.Text(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('higher_is_better', sa.Boolean(), nullable=False),
        sa.Column('scraped_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['leaderboard_id'], ['leaderboards.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_name', 'leaderboard_id', 'benchmark', 'scraped_at', name='uq_rawscore')
    )


def downgrade():
    op.drop_table('raw_scores')
    op.drop_table('leaderboards') 