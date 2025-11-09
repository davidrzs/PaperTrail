"""Hybrid search implementation using PostgreSQL FTS + pgvector with RRF"""

import numpy as np
from typing import List, Tuple, Optional
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from src.embeddings import generate_embedding
from src.models import Paper


def fts_search(db: Session, query: str, limit: int = 50, user_id: Optional[int] = None) -> List[int]:
    """
    Perform full-text search using PostgreSQL tsvector.

    Args:
        db: Database session
        query: Search query
        limit: Maximum number of results
        user_id: Optional user ID to include their private papers

    Returns:
        List of paper IDs ordered by relevance (ts_rank)
    """
    # Convert query to tsquery format (handle spaces and special characters)
    # Using plainto_tsquery for simple queries
    if user_id is not None:
        result = db.execute(
            text("""
                SELECT id
                FROM papers
                WHERE search_vector @@ plainto_tsquery('english', :query)
                  AND (is_private = false OR user_id = :user_id)
                ORDER BY ts_rank(search_vector, plainto_tsquery('english', :query)) DESC
                LIMIT :limit
            """),
            {"query": query, "limit": limit, "user_id": user_id}
        )
    else:
        result = db.execute(
            text("""
                SELECT id
                FROM papers
                WHERE search_vector @@ plainto_tsquery('english', :query)
                  AND is_private = false
                ORDER BY ts_rank(search_vector, plainto_tsquery('english', :query)) DESC
                LIMIT :limit
            """),
            {"query": query, "limit": limit}
        )

    return [row[0] for row in result.fetchall()]


def vector_search(
    db: Session,
    query_embedding: np.ndarray,
    limit: int = 50,
    user_id: Optional[int] = None
) -> List[Tuple[int, float]]:
    """
    Perform vector similarity search using pgvector.

    Uses cosine distance operator (<=> ) for efficient similarity search.

    Args:
        db: Database session
        query_embedding: Query embedding vector
        limit: Maximum number of results
        user_id: Optional user ID to include their private papers

    Returns:
        List of (paper_id, distance) tuples ordered by similarity
    """
    # Convert numpy array to list for PostgreSQL
    query_vector = query_embedding.tolist()

    # Use pgvector's cosine distance operator (<=>)
    if user_id is not None:
        result = db.execute(
            text("""
                SELECT e.paper_id, e.embedding_vector <=> :query_vector AS distance
                FROM embeddings e
                JOIN papers p ON e.paper_id = p.id
                WHERE p.is_private = false OR p.user_id = :user_id
                ORDER BY distance
                LIMIT :limit
            """),
            {"query_vector": str(query_vector), "limit": limit, "user_id": user_id}
        )
    else:
        result = db.execute(
            text("""
                SELECT e.paper_id, e.embedding_vector <=> :query_vector AS distance
                FROM embeddings e
                JOIN papers p ON e.paper_id = p.id
                WHERE p.is_private = false
                ORDER BY distance
                LIMIT :limit
            """),
            {"query_vector": str(query_vector), "limit": limit}
        )

    return [(row[0], float(row[1])) for row in result.fetchall()]


def reciprocal_rank_fusion(
    fts_results: List[int],
    vec_results: List[Tuple[int, float]],
    k: int = 60
) -> List[Tuple[int, float]]:
    """
    Combine FTS and vector search results using Reciprocal Rank Fusion.

    RRF formula: score(doc) = sum(1 / (k + rank(doc)))

    Args:
        fts_results: List of paper IDs from FTS search (ordered by relevance)
        vec_results: List of (paper_id, distance) from vector search
        k: RRF constant (default 60)

    Returns:
        List of (paper_id, rrf_score) sorted by score descending
    """
    rank_dict = {}

    # Process FTS results
    for rank, paper_id in enumerate(fts_results):
        if paper_id not in rank_dict:
            rank_dict[paper_id] = 0
        rank_dict[paper_id] += 1 / (k + rank + 1)

    # Process vector results
    for rank, (paper_id, distance) in enumerate(vec_results):
        if paper_id not in rank_dict:
            rank_dict[paper_id] = 0
        rank_dict[paper_id] += 1 / (k + rank + 1)

    # Sort by RRF score (descending)
    sorted_results = sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)

    return sorted_results


def hybrid_search(
    db: Session,
    query: str,
    limit: int = 50,
    user_id: Optional[int] = None
) -> List[Tuple[int, float]]:
    """
    Perform hybrid search combining FTS5 and vector similarity.

    Args:
        db: Database session
        query: Search query
        limit: Maximum number of results
        user_id: Optional user ID to include their private papers

    Returns:
        List of (paper_id, rrf_score) ordered by relevance
    """
    # Perform FTS search with privacy filtering
    fts_results = fts_search(db, query, limit=limit, user_id=user_id)

    # Generate query embedding and perform vector search
    query_embedding = generate_embedding(query)
    vec_results = vector_search(db, query_embedding, limit=limit, user_id=user_id)

    # Combine results with RRF
    combined_results = reciprocal_rank_fusion(fts_results, vec_results, k=60)

    return combined_results[:limit]
