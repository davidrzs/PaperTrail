"""Hybrid search implementation using FTS5 + vector similarity with RRF"""

import numpy as np
from typing import List, Tuple, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.embeddings import generate_embedding
from src.models import Paper


def fts_search(db: Session, query: str, limit: int = 50, is_authenticated: bool = False) -> List[int]:
    """
    Perform full-text search using SQLite FTS5.

    Args:
        db: Database session
        query: Search query
        limit: Maximum number of results
        is_authenticated: Whether user is authenticated (shows all papers if True)

    Returns:
        List of paper IDs ordered by relevance
    """
    # Use FTS5 MATCH for full-text search, then filter by privacy
    if is_authenticated:
        # Authenticated user sees all papers
        result = db.execute(
            text("""
                SELECT papers_fts.rowid FROM papers_fts
                JOIN papers ON papers.id = papers_fts.rowid
                WHERE papers_fts MATCH :query
                ORDER BY rank
                LIMIT :limit
            """),
            {"query": query, "limit": limit}
        )
    else:
        # Anonymous users see only public papers
        result = db.execute(
            text("""
                SELECT papers_fts.rowid FROM papers_fts
                JOIN papers ON papers.id = papers_fts.rowid
                WHERE papers_fts MATCH :query
                  AND papers.is_private = 0
                ORDER BY rank
                LIMIT :limit
            """),
            {"query": query, "limit": limit}
        )

    return [row[0] for row in result.fetchall()]


def vector_search(
    db: Session,
    query_embedding: np.ndarray,
    limit: int = 50,
    is_authenticated: bool = False
) -> List[Tuple[int, float]]:
    """
    Perform vector similarity search.

    For now, this does a brute-force cosine similarity search.
    TODO: Use sqlite-vec for optimized vector search once we set it up.

    Args:
        db: Database session
        query_embedding: Query embedding vector
        limit: Maximum number of results
        is_authenticated: Whether user is authenticated (shows all papers if True)

    Returns:
        List of (paper_id, distance) tuples ordered by similarity
    """
    from src.models import Embedding

    # Get all embeddings from database
    embeddings_query = db.query(Embedding.paper_id, Embedding.embedding_vector)

    # Filter by visibility based on authentication
    if is_authenticated:
        # Authenticated user sees all papers
        embeddings_query = embeddings_query.join(Paper)
    else:
        # Anonymous users see only public papers
        embeddings_query = embeddings_query.join(Paper).filter(Paper.is_private == False)

    embeddings = embeddings_query.all()

    if not embeddings:
        return []

    # Calculate cosine similarity for each embedding
    results = []
    query_norm = np.linalg.norm(query_embedding)

    for paper_id, embedding_blob in embeddings:
        # Convert blob back to numpy array
        paper_embedding = np.frombuffer(embedding_blob, dtype=np.float32)

        # Cosine similarity
        similarity = np.dot(query_embedding, paper_embedding) / (
            query_norm * np.linalg.norm(paper_embedding)
        )

        # Convert to distance (1 - similarity)
        distance = 1 - similarity
        results.append((paper_id, float(distance)))

    # Sort by distance (ascending = most similar first)
    results.sort(key=lambda x: x[1])

    return results[:limit]


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
    is_authenticated: bool = False
) -> List[Tuple[int, float]]:
    """
    Perform hybrid search combining FTS5 and vector similarity.

    Args:
        db: Database session
        query: Search query
        limit: Maximum number of results
        is_authenticated: Whether user is authenticated (shows all papers if True)

    Returns:
        List of (paper_id, rrf_score) ordered by relevance
    """
    # Perform FTS search with privacy filtering
    fts_results = fts_search(db, query, limit=limit, is_authenticated=is_authenticated)

    # Generate query embedding and perform vector search
    query_embedding = generate_embedding(query)
    vec_results = vector_search(db, query_embedding, limit=limit, is_authenticated=is_authenticated)

    # Combine results with RRF
    combined_results = reciprocal_rank_fusion(fts_results, vec_results, k=60)

    return combined_results[:limit]
