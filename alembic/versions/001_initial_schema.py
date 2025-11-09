"""Initial schema with pgvector and full-text search

Revision ID: 001
Revises:
Create Date: 2025-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('show_heatmap', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tags_id', 'tags', ['id'])
    op.create_index('ix_tags_name', 'tags', ['name'])
    op.create_index('ix_tags_user_id', 'tags', ['user_id'])

    # Create papers table
    op.create_table(
        'papers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('authors', sa.String(length=500), nullable=False),
        sa.Column('arxiv_id', sa.String(length=50), nullable=True),
        sa.Column('doi', sa.String(length=100), nullable=True),
        sa.Column('paper_url', sa.String(length=500), nullable=True),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('is_private', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('date_read', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_papers_id', 'papers', ['id'])
    op.create_index('ix_papers_user_id', 'papers', ['user_id'])
    op.create_index('ix_papers_is_private', 'papers', ['is_private'])
    op.create_index('ix_papers_created_at', 'papers', ['created_at'])

    # Add tsvector column for full-text search
    op.execute("""
        ALTER TABLE papers ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(authors, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(abstract, '')), 'C') ||
                setweight(to_tsvector('english', coalesce(summary, '')), 'D')
            ) STORED
    """)

    # Create GIN index for full-text search
    op.create_index('ix_papers_search_vector', 'papers', ['search_vector'], postgresql_using='gin')

    # Create paper_tags association table
    op.create_table(
        'paper_tags',
        sa.Column('paper_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['paper_id'], ['papers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('paper_id', 'tag_id')
    )

    # Create embeddings table with pgvector
    # Using 896 dimensions for Qwen3-Embedding-0.6B
    op.create_table(
        'embeddings',
        sa.Column('paper_id', sa.Integer(), nullable=False),
        sa.Column('embedding_vector', Vector(896), nullable=False),
        sa.Column('embedding_source', sa.String(length=50), nullable=False, server_default='abstract_summary'),
        sa.ForeignKeyConstraint(['paper_id'], ['papers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('paper_id')
    )

    # Create ivfflat index for vector similarity search (cosine distance)
    # Note: This index should be created AFTER populating some data for better performance
    # For now, we'll create it. In production, you might want to create this manually after loading data.
    op.execute("""
        CREATE INDEX embedding_vector_idx ON embeddings
        USING ivfflat (embedding_vector vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    op.drop_index('embedding_vector_idx', table_name='embeddings')
    op.drop_table('embeddings')
    op.drop_table('paper_tags')
    op.drop_index('ix_papers_search_vector', table_name='papers')
    op.execute('ALTER TABLE papers DROP COLUMN search_vector')
    op.drop_index('ix_papers_created_at', table_name='papers')
    op.drop_index('ix_papers_is_private', table_name='papers')
    op.drop_index('ix_papers_user_id', table_name='papers')
    op.drop_index('ix_papers_id', table_name='papers')
    op.drop_table('papers')
    op.drop_index('ix_tags_user_id', table_name='tags')
    op.drop_index('ix_tags_name', table_name='tags')
    op.drop_index('ix_tags_id', table_name='tags')
    op.drop_table('tags')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS vector')
