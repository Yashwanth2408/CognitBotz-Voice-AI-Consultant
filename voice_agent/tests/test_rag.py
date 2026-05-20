"""
tests/test_rag.py
-----------------
Unit and integration tests for the RAG pipeline.

Tests chunking, embedding, FAISS search, and retrieval quality.
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path

# Add the project root to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ─────────────────────────────────────────────
# Chunking Tests
# ─────────────────────────────────────────────

class TestChunking:

    def test_chunk_produces_documents(self):
        """Chunking should return a non-empty list of Documents."""
        from rag.chunking import chunk_knowledge_base
        from config.settings import KNOWLEDGE_BASE_PATH

        if not KNOWLEDGE_BASE_PATH.exists():
            pytest.skip("Knowledge base not found — run from project root")

        docs = chunk_knowledge_base()
        assert len(docs) > 0, "Chunking returned no documents"

    def test_chunk_metadata_contains_source(self):
        """Every chunk should have display_source metadata set."""
        from rag.chunking import chunk_knowledge_base
        from config.settings import KNOWLEDGE_BASE_PATH

        if not KNOWLEDGE_BASE_PATH.exists():
            pytest.skip("Knowledge base not found")

        docs = chunk_knowledge_base()
        for doc in docs[:10]:
            assert "display_source" in doc.metadata, (
                f"Chunk missing display_source metadata: {doc.page_content[:60]}"
            )

    def test_chunk_size_within_limit(self):
        """No chunk should significantly exceed the configured chunk size."""
        from rag.chunking import chunk_knowledge_base
        from config.settings import KNOWLEDGE_BASE_PATH, CHUNK_SIZE

        if not KNOWLEDGE_BASE_PATH.exists():
            pytest.skip("Knowledge base not found")

        docs = chunk_knowledge_base()
        oversized = [
            d for d in docs
            if len(d.page_content) > CHUNK_SIZE * 2  # Allow 2x tolerance
        ]
        assert len(oversized) == 0, (
            f"{len(oversized)} chunks exceed 2x the chunk size limit"
        )

    def test_chunk_content_not_empty(self):
        """No chunk should have empty page content."""
        from rag.chunking import chunk_knowledge_base
        from config.settings import KNOWLEDGE_BASE_PATH

        if not KNOWLEDGE_BASE_PATH.exists():
            pytest.skip("Knowledge base not found")

        docs = chunk_knowledge_base()
        empty = [d for d in docs if not d.page_content.strip()]
        assert len(empty) == 0, f"{len(empty)} chunks have empty content"

    def test_known_content_appears_in_chunks(self):
        """Key company facts should be present in the chunked output."""
        from rag.chunking import chunk_knowledge_base
        from config.settings import KNOWLEDGE_BASE_PATH

        if not KNOWLEDGE_BASE_PATH.exists():
            pytest.skip("Knowledge base not found")

        docs = chunk_knowledge_base()
        all_text = " ".join(d.page_content for d in docs)

        expected_phrases = ["CognitBotz", "Hyderabad", "Groq", "FAISS"]
        for phrase in expected_phrases:
            assert phrase.lower() in all_text.lower(), (
                f"Expected phrase '{phrase}' not found in any chunk"
            )


# ─────────────────────────────────────────────
# Embedding Tests
# ─────────────────────────────────────────────

class TestEmbeddings:

    def test_embed_query_returns_vector(self):
        """embed_query should return a non-empty float list."""
        from rag.embeddings import embed_query
        from config.constants import BGE_EMBEDDING_DIM

        vector = embed_query("What services does CognitBotz offer?")
        assert isinstance(vector, list), "embed_query should return a list"
        assert len(vector) == BGE_EMBEDDING_DIM, (
            f"Expected {BGE_EMBEDDING_DIM}-dim vector, got {len(vector)}"
        )
        assert all(isinstance(v, float) for v in vector), (
            "Vector elements should be floats"
        )

    def test_embed_documents_batch(self):
        """embed_documents should handle a batch of texts."""
        from rag.embeddings import embed_documents

        texts = [
            "CognitBotz provides AI automation.",
            "XTTS-v2 synthesises natural voice.",
            "FAISS is used for vector search.",
        ]
        vectors = embed_documents(texts)
        assert len(vectors) == len(texts), (
            "Should return one vector per input text"
        )

    def test_different_queries_produce_different_vectors(self):
        """Distinct queries should produce distinct embedding vectors."""
        from rag.embeddings import embed_query
        import numpy as np

        v1 = embed_query("What is XTTS-v2?")
        v2 = embed_query("What is FAISS?")
        cosine_sim = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

        # Completely different topics should have cosine similarity below 0.98
        assert cosine_sim < 0.98, (
            f"Too similar: cosine={cosine_sim:.4f}. Embeddings may be identical."
        )


# ─────────────────────────────────────────────
# FAISS / Retrieval Tests
# ─────────────────────────────────────────────

class TestRetrieval:

    def test_faiss_index_loads(self):
        """FAISS index should load without error if ingestion has been run."""
        from rag.vector_store import load_faiss_index, index_exists
        from config.settings import FAISS_INDEX_DIR

        if not index_exists(FAISS_INDEX_DIR):
            pytest.skip("FAISS index not built — run: python run_ingestion.py")

        store = load_faiss_index()
        assert store is not None
        assert store.index.ntotal > 0, "FAISS index is empty"

    def test_retrieval_returns_results(self):
        """A relevant query should return at least one document."""
        from rag.vector_store import load_faiss_index, index_exists
        from rag.retrieval import KnowledgeRetriever

        if not index_exists():
            pytest.skip("FAISS index not built")

        store = load_faiss_index()
        retriever = KnowledgeRetriever(store)
        result = retriever.retrieve("What AI services does CognitBotz offer?")

        assert result.has_results, "Expected at least one retrieved chunk"
        assert result.context_text, "Context text should not be empty"

    def test_retrieval_source_labels_present(self):
        """Retrieval results should include source label metadata."""
        from rag.vector_store import load_faiss_index, index_exists
        from rag.retrieval import KnowledgeRetriever

        if not index_exists():
            pytest.skip("FAISS index not built")

        store = load_faiss_index()
        retriever = KnowledgeRetriever(store)
        result = retriever.retrieve("Tell me about CognitBotz case studies")

        if result.has_results:
            for label in result.source_labels:
                assert isinstance(label, str) and len(label) > 0, (
                    "All source labels should be non-empty strings"
                )

    def test_irrelevant_query_below_threshold(self):
        """An unrelated query should return few or no results."""
        from rag.vector_store import load_faiss_index, index_exists
        from rag.retrieval import KnowledgeRetriever

        if not index_exists():
            pytest.skip("FAISS index not built")

        store = load_faiss_index()
        retriever = KnowledgeRetriever(store, score_threshold=0.7)
        # Very high threshold makes it hard to match anything irrelevant
        result = retriever.retrieve(
            "xkcd random gibberish quantum banana zzt4729", score_threshold=0.95
        )
        # With a very high threshold, a nonsense query should return nothing
        assert len(result.documents) == 0, (
            "Gibberish query returned results above a 0.95 threshold"
        )
