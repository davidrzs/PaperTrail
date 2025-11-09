"""Embedding generation using EmbeddingGemma model"""

import os
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import Optional

from src.config import settings

# Load HF token from environment
HF_TOKEN = os.getenv("HF_TOKEN")

# Global model instance (loaded once on startup)
_model: Optional[SentenceTransformer] = None

# EmbeddingGemma supports 2048 tokens max
MAX_TEXT_LENGTH = 8000  # Conservative char limit (~2048 tokens)


def load_model() -> SentenceTransformer:
    """
    Load the EmbeddingGemma model.

    This should be called once on application startup.
    The model is cached globally for subsequent calls.
    """
    global _model

    if _model is None:
        print(f"Loading embedding model: {settings.embedding_model}")
        _model = SentenceTransformer(
            settings.embedding_model,
            token=HF_TOKEN
        )
        print(f"Model loaded successfully. Embedding dimension: {_model.get_sentence_embedding_dimension()}")

    return _model


def get_model() -> SentenceTransformer:
    """Get the loaded model instance"""
    if _model is None:
        return load_model()
    return _model


def truncate_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """
    Truncate text to max_length characters if needed.

    Args:
        text: Input text
        max_length: Maximum character length

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length]


def generate_embedding(text: str) -> np.ndarray:
    """
    Generate embedding for a query text using EmbeddingGemma.

    Args:
        text: Input query text to embed

    Returns:
        Numpy array of embedding vector (768 dimensions)
    """
    model = get_model()

    # Truncate if too long
    text = truncate_text(text)

    # Use encode_query for query text (applies task-specific prompt)
    embedding = model.encode_query(text)

    return embedding


def generate_paper_embedding(abstract: Optional[str], summary: str) -> np.ndarray:
    """
    Generate embedding for a paper by combining abstract and summary.

    Args:
        abstract: Optional paper abstract
        summary: Paper summary (required)

    Returns:
        Numpy array of embedding vector (768 dimensions)
    """
    model = get_model()

    # Combine abstract (if present) and summary
    parts = []
    if abstract:
        parts.append(abstract)
    parts.append(summary)

    text = "\n\n".join(parts)

    # Truncate if too long
    text = truncate_text(text)

    # Use encode_document for paper text (applies document-specific prompt)
    embedding = model.encode_document(text)

    return embedding


def get_embedding_dimension() -> int:
    """Get the dimension of embeddings from the model"""
    model = get_model()
    return model.get_sentence_embedding_dimension()


if __name__ == "__main__":
    """Test embedding generation"""
    # Load model
    model = load_model()

    # Test embedding
    test_text = "Attention is all you need introduces the Transformer architecture"
    embedding = generate_embedding(test_text)

    print(f"Test embedding generated")
    print(f"Dimension: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")
