"""
rag/embeddings.py
-----------------
Embedding model management using BAAI/bge-small-en-v1.5.

Design rationale:
  - BGE (BAAI General Embedding) small v1.5 selected per spec section 11.
  - Model is cached as a module-level singleton to avoid reload on every call.
  - BGE retrieval models require a query prefix for asymmetric retrieval;
    document chunks are embedded without prefix, queries with it.
  - HuggingFaceEmbeddings wraps sentence-transformers for LangChain compatibility.
"""

from functools import lru_cache
from typing import Optional

from langchain_huggingface import HuggingFaceEmbeddings

from config.settings import EMBEDDING_MODEL_NAME, EMBEDDINGS_CACHE_DIR
from config.constants import BGE_QUERY_PREFIX
from utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Load and cache the BGE-small-en-v1.5 embedding model.

    The model is loaded once and held in memory for the lifetime of the process.
    lru_cache(maxsize=1) ensures a single instance regardless of call count.

    Model download is automatic on first run (~130 MB).
    Subsequent runs use the local cache at ~/.cache/huggingface.

    Returns:
        Configured HuggingFaceEmbeddings instance.
    """
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")

    # Ensure the local embeddings cache directory exists
    EMBEDDINGS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={
            "device": _get_device(),
        },
        encode_kwargs={
            # Normalise embeddings to unit length for cosine similarity.
            # Required for meaningful L2 distance comparisons in FAISS.
            "normalize_embeddings": True,
        },
        cache_folder=str(EMBEDDINGS_CACHE_DIR),
    )

    logger.info("Embedding model loaded successfully.")
    return model


def embed_documents(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for knowledge base document chunks.

    Documents are embedded WITHOUT the BGE query prefix — this is
    intentional for asymmetric retrieval where queries use a prefix
    and documents do not.

    Args:
        texts: List of chunk text strings.

    Returns:
        List of embedding vectors (each 384-dimensional for BGE-small).
    """
    model = get_embedding_model()
    logger.debug(f"Embedding {len(texts)} document chunks")
    return model.embed_documents(texts)


def embed_query(query: str) -> list[float]:
    """
    Generate an embedding for a user query.

    Prepends the BGE query prefix before embedding. This asymmetric
    approach improves retrieval precision — the model was trained this way.

    Args:
        query: User question or search string.

    Returns:
        384-dimensional embedding vector.
    """
    model = get_embedding_model()
    # Prefix is part of BGE's retrieval protocol, not user-visible
    prefixed_query = f"{BGE_QUERY_PREFIX}{query}"
    return model.embed_query(prefixed_query)


def _get_device() -> str:
    """
    Detect the best available compute device for embedding inference.

    Returns 'cuda' if a GPU is available, otherwise 'cpu'.
    Embeddings are fast enough on CPU for production use at our scale.
    """
    try:
        import torch
        if torch.cuda.is_available():
            logger.info("CUDA GPU detected — using GPU for embeddings")
            return "cuda"
    except ImportError:
        pass
    logger.info("Using CPU for embeddings")
    return "cpu"
