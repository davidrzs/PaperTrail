"""Embedding generation using Qwen3-Embedding-0.6B model"""

import numpy as np
from sentence_transformers import SentenceTransformer
from typing import Optional

from src.config import settings

# Global model instance (loaded once on startup)
_model: Optional[SentenceTransformer] = None


def load_model() -> SentenceTransformer:
    """
    Load the Qwen3-Embedding-0.6B model.

    This should be called once on application startup.
    The model is cached globally for subsequent calls.
    """
    global _model

    if _model is None:
        print(f"Loading embedding model: {settings.embedding_model}")
        _model = SentenceTransformer(settings.embedding_model)
        print(f"Model loaded successfully. Embedding dimension: {_model.get_sentence_embedding_dimension()}")

    return _model


def get_model() -> SentenceTransformer:
    """Get the loaded model instance"""
    if _model is None:
        return load_model()
    return _model


def generate_embedding(text: str) -> np.ndarray:
    """
    Generate embedding for a given text using Qwen model.

    Args:
        text: Input text to embed

    Returns:
        Numpy array of embedding vector
    """
    model = get_model()

    # Use query prompt for better search results
    embedding = model.encode([text], prompt_name="query")[0]

    return embedding


def generate_paper_embedding(abstract: Optional[str], summary: str) -> np.ndarray:
    """
    Generate embedding for a paper by combining abstract and summary.

    Args:
        abstract: Optional paper abstract
        summary: Paper summary (required)

    Returns:
        Numpy array of embedding vector
    """
    # Combine abstract (if present) and summary
    parts = []
    if abstract:
        parts.append(abstract)
    parts.append(summary)

    text = "\n\n".join(parts)

    return generate_embedding(text)


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
