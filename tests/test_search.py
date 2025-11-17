"""Tests for hybrid search functionality"""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.embeddings import generate_embedding, generate_paper_embedding, load_model
from src.models import Embedding, Paper
from src.search import fts_search, hybrid_search, reciprocal_rank_fusion, vector_search


class TestEmbeddings:
    """Test embedding generation"""

    def test_load_model(self):
        """Test that the embedding model loads successfully"""
        model = load_model()
        assert model is not None
        # Verify model produces expected dimension (768 for EmbeddingGemma-300m)
        test_embedding = model.encode("test")
        assert test_embedding.shape[0] == 768

    def test_generate_embedding(self):
        """Test generating embeddings for text"""
        text = "Neural networks are computational models inspired by biological brains"
        embedding = generate_embedding(text)

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] == 768
        assert embedding.dtype == np.float32

    def test_generate_paper_embedding_with_abstract(self):
        """Test generating paper embeddings with both abstract and summary"""
        abstract = "This paper introduces a novel approach to machine learning"
        summary = "We propose a new ML technique that improves accuracy"

        embedding = generate_paper_embedding(abstract, summary)

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] == 768

    def test_generate_paper_embedding_without_abstract(self):
        """Test generating paper embeddings with only summary (no abstract)"""
        summary = "We propose a new ML technique that improves accuracy"

        embedding = generate_paper_embedding(None, summary)

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] == 768

    def test_embedding_similarity(self):
        """Test that similar texts produce similar embeddings"""
        text1 = "machine learning and artificial intelligence"
        text2 = "AI and ML techniques"
        text3 = "cooking recipes and food preparation"

        emb1 = generate_embedding(text1)
        emb2 = generate_embedding(text2)
        emb3 = generate_embedding(text3)

        # Cosine similarity between related texts should be higher
        sim_12 = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        sim_13 = np.dot(emb1, emb3) / (np.linalg.norm(emb1) * np.linalg.norm(emb3))

        assert sim_12 > sim_13


class TestPaperCreationWithEmbeddings:
    """Test that embeddings are automatically generated when creating papers"""

    def test_create_paper_generates_embedding(self, authenticated_client: TestClient, db_session):
        """Test that creating a paper automatically generates and stores an embedding"""
        paper_data = {
            "title": "Attention Is All You Need",
            "authors": "Vaswani et al.",
            "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks",
            "summary": "Introduces the Transformer architecture using only attention mechanisms",
            "tags": ["nlp", "transformers"],
            "is_private": False
        }

        response = authenticated_client.post("/papers", json=paper_data)
        assert response.status_code == 201

        paper_id = response.json()["id"]

        # Verify embedding was created in database
        embedding = db_session.query(Embedding).filter(Embedding.paper_id == paper_id).first()

        assert embedding is not None
        assert embedding.embedding_vector is not None
        assert embedding.embedding_source == "abstract_summary"

        # Verify embedding can be decoded
        embedding_array = np.frombuffer(embedding.embedding_vector, dtype=np.float32)
        assert embedding_array.shape[0] == 768

    def test_create_paper_without_abstract_generates_embedding(self, authenticated_client: TestClient, db_session):
        """Test that papers without abstracts still generate embeddings"""
        paper_data = {
            "title": "Short Paper Without Abstract",
            "authors": "John Doe",
            "summary": "This is a brief summary of the paper's main contribution",
            "tags": ["short"],
            "is_private": False
        }

        response = authenticated_client.post("/papers", json=paper_data)
        assert response.status_code == 201

        paper_id = response.json()["id"]

        # Verify embedding was created even without abstract
        embedding = db_session.query(Embedding).filter(Embedding.paper_id == paper_id).first()

        assert embedding is not None
        assert embedding.embedding_vector is not None


class TestFTSSearch:
    """Test full-text search functionality"""

    def test_fts_search_finds_exact_match(self, db_session):
        """Test FTS5 search finds papers with exact keyword matches"""
        # Create test papers
        paper1 = Paper(
            title="Deep Learning with Neural Networks",
            authors="Smith et al.",
            abstract="This paper explores deep neural networks",
            summary="We study deep learning techniques",
            is_private=False
        )
        paper2 = Paper(
            title="Quantum Computing Basics",
            authors="Jones et al.",
            abstract="Introduction to quantum algorithms",
            summary="Overview of quantum computing principles",
            is_private=False
        )
        db_session.add_all([paper1, paper2])
        db_session.commit()

        # Search for "neural" - authenticated user sees all papers
        results = fts_search(db_session, "neural", limit=10, is_authenticated=True)

        assert len(results) > 0
        assert paper1.id in results
        assert paper2.id not in results

    def test_fts_search_multi_word_query(self, db_session):
        """Test FTS5 search with multi-word queries"""
        paper = Paper(
            title="Transformer Architecture for NLP",
            authors="Brown et al.",
            abstract="We present a novel transformer-based approach",
            summary="Transformer models achieve state-of-the-art results",
            is_private=False
        )
        db_session.add(paper)
        db_session.commit()

        # Search for multiple words
        results = fts_search(db_session, "transformer nlp", limit=10, is_authenticated=True)

        assert len(results) > 0
        assert paper.id in results

    def test_fts_search_respects_privacy(self, db_session):
        """Test that FTS search respects privacy settings"""
        public_paper = Paper(
            title="Public Neural Network Paper",
            authors="Smith",
            summary="Public research on neural networks",
            is_private=False
        )
        private_paper = Paper(
            title="Private Neural Network Paper",
            authors="Smith",
            summary="Private research on neural networks",
            is_private=True
        )
        db_session.add_all([public_paper, private_paper])
        db_session.commit()

        # Search without authentication (is_authenticated=False) - should only find public
        results = fts_search(db_session, "neural", limit=10, is_authenticated=False)
        assert public_paper.id in results
        assert private_paper.id not in results

        # Search with authentication (is_authenticated=True) - should find both
        results = fts_search(db_session, "neural", limit=10, is_authenticated=True)
        assert public_paper.id in results
        assert private_paper.id in results


class TestVectorSearch:
    """Test vector similarity search functionality"""

    def test_vector_search_finds_semantic_matches(self, db_session):
        """Test vector search finds semantically similar papers"""
        # Create papers with semantically related content
        paper1 = Paper(
            title="Neural Networks for Image Recognition",
            authors="Lee et al.",
            abstract="Convolutional neural networks for computer vision",
            summary="CNNs achieve excellent results on image classification",
            is_private=False
        )
        paper2 = Paper(
            title="Quantum Cryptography Protocols",
            authors="Wang et al.",
            abstract="Secure communication using quantum mechanics",
            summary="Quantum key distribution for secure messaging",
            is_private=False
        )
        db_session.add_all([paper1, paper2])
        db_session.commit()

        # Generate and store embeddings
        for paper in [paper1, paper2]:
            embedding_vector = generate_paper_embedding(paper.abstract, paper.summary)
            embedding_blob = embedding_vector.astype(np.float32).tobytes()
            db_embedding = Embedding(
                paper_id=paper.id,
                embedding_vector=embedding_blob,
                embedding_source="abstract_summary"
            )
            db_session.add(db_embedding)
        db_session.commit()

        # Search for "deep learning for vision tasks"
        query_embedding = generate_embedding("deep learning for vision tasks")
        results = vector_search(db_session, query_embedding, limit=10, is_authenticated=True)

        # Should find paper1 with higher rank than paper2
        paper_ids = [paper_id for paper_id, distance in results]
        assert paper1.id in paper_ids

        # Paper1 should be ranked higher (appear earlier) than paper2
        if paper2.id in paper_ids:
            idx1 = paper_ids.index(paper1.id)
            idx2 = paper_ids.index(paper2.id)
            assert idx1 < idx2

    def test_vector_search_respects_privacy(self, db_session):
        """Test that vector search respects privacy settings"""
        public_paper = Paper(
            title="Public ML Paper",
            authors="Smith",
            summary="Machine learning techniques",
            is_private=False
        )
        private_paper = Paper(
            title="Private ML Paper",
            authors="Smith",
            summary="Machine learning techniques",
            is_private=True
        )
        db_session.add_all([public_paper, private_paper])
        db_session.commit()

        # Generate embeddings for both
        for paper in [public_paper, private_paper]:
            embedding_vector = generate_paper_embedding(paper.abstract, paper.summary)
            embedding_blob = embedding_vector.astype(np.float32).tobytes()
            db_embedding = Embedding(
                paper_id=paper.id,
                embedding_vector=embedding_blob,
                embedding_source="abstract_summary"
            )
            db_session.add(db_embedding)
        db_session.commit()

        query_embedding = generate_embedding("machine learning")

        # Anonymous search (is_authenticated=False) - only public
        results = vector_search(db_session, query_embedding, limit=10, is_authenticated=False)
        paper_ids = [paper_id for paper_id, distance in results]
        assert public_paper.id in paper_ids
        assert private_paper.id not in paper_ids

        # Authenticated search (is_authenticated=True) - both
        results = vector_search(db_session, query_embedding, limit=10, is_authenticated=True)
        paper_ids = [paper_id for paper_id, distance in results]
        assert public_paper.id in paper_ids
        assert private_paper.id in paper_ids


class TestRRF:
    """Test Reciprocal Rank Fusion algorithm"""

    def test_rrf_combines_rankings(self):
        """Test RRF correctly combines FTS and vector rankings"""
        fts_results = [1, 2, 3, 4]  # Paper IDs from FTS search
        vec_results = [(3, 0.1), (1, 0.2), (5, 0.3), (2, 0.4)]  # (paper_id, distance) from vector search

        combined = reciprocal_rank_fusion(fts_results, vec_results, k=60)

        # Should return list of (paper_id, score) tuples sorted by score
        assert len(combined) == 5  # 1, 2, 3, 4, 5
        assert all(isinstance(item, tuple) and len(item) == 2 for item in combined)

        # Papers appearing in both lists should have higher scores
        paper_ids = [paper_id for paper_id, score in combined]
        scores = {paper_id: score for paper_id, score in combined}

        # Papers 1, 2, 3 appear in both, should have higher scores than 4 and 5
        assert scores[1] > scores[4]
        assert scores[2] > scores[4]
        assert scores[3] > scores[5]

    def test_rrf_empty_inputs(self):
        """Test RRF handles empty result sets"""
        result = reciprocal_rank_fusion([], [], k=60)
        assert result == []

        result = reciprocal_rank_fusion([1, 2], [], k=60)
        assert len(result) == 2

        result = reciprocal_rank_fusion([], [(1, 0.1), (2, 0.2)], k=60)
        assert len(result) == 2


class TestHybridSearch:
    """Test hybrid search combining FTS and vector search"""

    def test_hybrid_search_combines_both_methods(self, db_session):
        """Test hybrid search uses both FTS and vector search"""
        # Create papers that would rank differently in FTS vs vector search
        paper1 = Paper(
            title="Transformer transformer transformer",  # High FTS score for "transformer"
            authors="Smith",
            abstract="This paper uses transformers extensively",
            summary="Lots of transformer mentions here transformer transformer",
            is_private=False
        )
        paper2 = Paper(
            title="Attention Mechanisms in Neural Networks",  # High semantic similarity
            authors="Jones",
            abstract="Self-attention and multi-head attention for sequence modeling",
            summary="Novel attention-based architecture for NLP tasks",
            is_private=False
        )
        db_session.add_all([paper1, paper2])
        db_session.commit()

        # Generate embeddings
        for paper in [paper1, paper2]:
            embedding_vector = generate_paper_embedding(paper.abstract, paper.summary)
            embedding_blob = embedding_vector.astype(np.float32).tobytes()
            db_embedding = Embedding(
                paper_id=paper.id,
                embedding_vector=embedding_blob,
                embedding_source="abstract_summary"
            )
            db_session.add(db_embedding)
        db_session.commit()

        # Search for "transformer architecture"
        results = hybrid_search(db_session, "transformer architecture", limit=10, is_authenticated=True)

        # Should return both papers with RRF scores
        assert len(results) > 0
        paper_ids = [paper_id for paper_id, score in results]
        assert paper1.id in paper_ids or paper2.id in paper_ids

    def test_hybrid_search_respects_privacy(self, db_session):
        """Test hybrid search respects privacy settings"""
        public_paper = Paper(
            title="Public Research on Transformers",
            authors="Smith",
            summary="Public transformer research",
            is_private=False
        )
        private_paper = Paper(
            title="Private Research on Transformers",
            authors="Smith",
            summary="Private transformer research",
            is_private=True
        )
        db_session.add_all([public_paper, private_paper])
        db_session.commit()

        # Generate embeddings
        for paper in [public_paper, private_paper]:
            embedding_vector = generate_paper_embedding(paper.abstract, paper.summary)
            embedding_blob = embedding_vector.astype(np.float32).tobytes()
            db_embedding = Embedding(
                paper_id=paper.id,
                embedding_vector=embedding_blob,
                embedding_source="abstract_summary"
            )
            db_session.add(db_embedding)
        db_session.commit()

        # Anonymous search (is_authenticated=False)
        results = hybrid_search(db_session, "transformer", limit=10, is_authenticated=False)
        paper_ids = [paper_id for paper_id, score in results]
        assert public_paper.id in paper_ids
        assert private_paper.id not in paper_ids

        # Authenticated search (is_authenticated=True)
        results = hybrid_search(db_session, "transformer", limit=10, is_authenticated=True)
        paper_ids = [paper_id for paper_id, score in results]
        assert public_paper.id in paper_ids
        assert private_paper.id in paper_ids


class TestSearchAPI:
    """Test the search API endpoint"""

    def test_search_endpoint_returns_json_for_api(self, authenticated_client: TestClient, db_session):
        """Test search endpoint returns JSON for regular API calls"""
        # Create test paper
        paper = Paper(
            title="Neural Network Research",
            authors="Test Author",
            summary="Research on neural networks and deep learning",
            is_private=False
        )
        db_session.add(paper)
        db_session.commit()

        # Generate embedding
        embedding_vector = generate_paper_embedding(paper.abstract, paper.summary)
        embedding_blob = embedding_vector.astype(np.float32).tobytes()
        db_embedding = Embedding(
            paper_id=paper.id,
            embedding_vector=embedding_blob,
            embedding_source="abstract_summary"
        )
        db_session.add(db_embedding)
        db_session.commit()

        # Make API request (no HX-Request header)
        response = authenticated_client.get("/papers/search?q=neural+networks")

        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert "query" in data
        assert "total" in data
        assert data["query"] == "neural networks"
        assert isinstance(data["results"], list)

    def test_search_endpoint_returns_html_for_htmx(self, authenticated_client: TestClient, db_session):
        """Test search endpoint returns HTML for HTMX requests"""
        # Create test paper
        paper = Paper(
            title="Machine Learning Basics",
            authors="Test Author",
            summary="Introduction to machine learning concepts",
            is_private=False
        )
        db_session.add(paper)
        db_session.commit()

        # Generate embedding
        embedding_vector = generate_paper_embedding(paper.abstract, paper.summary)
        embedding_blob = embedding_vector.astype(np.float32).tobytes()
        db_embedding = Embedding(
            paper_id=paper.id,
            embedding_vector=embedding_blob,
            embedding_source="abstract_summary"
        )
        db_session.add(db_embedding)
        db_session.commit()

        # Make HTMX request
        response = authenticated_client.get(
            "/papers/search?q=machine+learning",
            headers={"HX-Request": "true"}
        )

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

        # Check HTML contains expected elements
        html = response.text
        assert "papers-list" in html or "search-info" in html

    def test_search_with_no_results(self, authenticated_client: TestClient):
        """Test search returns appropriate response when no results found"""
        response = authenticated_client.get("/papers/search?q=nonexistentquery12345")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert len(data["results"]) == 0

    def test_search_respects_limit_parameter(self, authenticated_client: TestClient, db_session):
        """Test search respects the limit parameter"""
        # Create multiple papers
        for i in range(5):
            paper = Paper(
                title=f"Neural Network Paper {i}",
                authors="Test Author",
                summary="Research on neural networks",
                is_private=False
            )
            db_session.add(paper)
        db_session.commit()

        # Generate embeddings
        papers = db_session.query(Paper).all()
        for paper in papers:
            embedding_vector = generate_paper_embedding(paper.abstract, paper.summary)
            embedding_blob = embedding_vector.astype(np.float32).tobytes()
            db_embedding = Embedding(
                paper_id=paper.id,
                embedding_vector=embedding_blob,
                embedding_source="abstract_summary"
            )
            db_session.add(db_embedding)
        db_session.commit()

        # Search with limit
        response = authenticated_client.get("/papers/search?q=neural&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 2
