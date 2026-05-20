"""
rag/vector_store.py
-------------------
FAISS vector store management — creation, persistence, and loading.

Design rationale:
  - FAISS (Facebook AI Similarity Search) selected per spec section 12.
  - IndexFlatL2 provides exact nearest-neighbour search. Given our knowledge
    base size (~200–500 chunks), exact search is fast and avoids approximate
    search accuracy trade-offs.
  - Persistence prevents rebuilding embeddings on every application launch.
  - Loading guard checks for existing index before creating a new one.
"""

from pathlib import Path
from typing import Optional

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from config.settings import FAISS_INDEX_DIR
from config.constants import FAISS_INDEX_FILENAME, FAISS_DOCSTORE_FILENAME
from rag.embeddings import get_embedding_model
from utils.logger import get_logger

logger = get_logger(__name__)


def build_faiss_index(documents: list[Document]) -> FAISS:
    """
    Build a new FAISS index from a list of LangChain Documents.

    Generates embeddings for all documents using the BGE model and
    stores them in a FAISS IndexFlatL2 structure.

    Args:
        documents: List of chunked knowledge base Documents with metadata.

    Returns:
        Populated FAISS vector store.

    Raises:
        ValueError: If documents list is empty.
    """
    if not documents:
        raise ValueError("Cannot build FAISS index: documents list is empty.")

    logger.info(f"Building FAISS index from {len(documents)} chunks...")

    embedding_model = get_embedding_model()

    # FAISS.from_documents handles both embedding generation and index construction.
    # It calls embed_documents() internally on each document's page_content.
    vector_store = FAISS.from_documents(
        documents=documents,
        embedding=embedding_model,
    )

    logger.info("FAISS index built successfully.")
    return vector_store


def save_faiss_index(
    vector_store: FAISS,
    index_dir: Optional[Path] = None,
) -> None:
    """
    Persist the FAISS index to disk for reuse across application launches.

    Saves two files:
    - index.faiss: The FAISS binary index (vectors + search structure)
    - index.pkl: The document store (text + metadata, serialised with pickle)

    Args:
        vector_store: Populated FAISS vector store.
        index_dir: Directory to save files. Defaults to settings.FAISS_INDEX_DIR.
    """
    save_dir = index_dir or FAISS_INDEX_DIR
    save_dir.mkdir(parents=True, exist_ok=True)

    vector_store.save_local(str(save_dir))
    logger.info(f"FAISS index saved to: {save_dir}")

    # Verify files exist after save
    for filename in [FAISS_INDEX_FILENAME, FAISS_DOCSTORE_FILENAME]:
        fpath = save_dir / filename
        size_kb = fpath.stat().st_size / 1024 if fpath.exists() else 0
        logger.info(f"  → {filename}: {size_kb:.1f} KB")


def load_faiss_index(
    index_dir: Optional[Path] = None,
) -> FAISS:
    """
    Load a persisted FAISS index from disk.

    Called at application startup to avoid rebuilding embeddings on every run.
    The index directory must contain both index.faiss and index.pkl.

    Args:
        index_dir: Directory containing the saved index files.
                   Defaults to settings.FAISS_INDEX_DIR.

    Returns:
        Loaded FAISS vector store ready for similarity search.

    Raises:
        FileNotFoundError: If the index files are not found.
    """
    load_dir = index_dir or FAISS_INDEX_DIR

    # Validate both required files exist before attempting load
    for filename in [FAISS_INDEX_FILENAME, FAISS_DOCSTORE_FILENAME]:
        fpath = load_dir / filename
        if not fpath.exists():
            raise FileNotFoundError(
                f"FAISS index file not found: {fpath}\n"
                f"Run: python run_ingestion.py to build the index."
            )

    embedding_model = get_embedding_model()

    # allow_dangerous_deserialization=True is required for LangChain FAISS loading
    # because the docstore uses pickle. This is safe in our controlled environment
    # where we generate and control the index files ourselves.
    vector_store = FAISS.load_local(
        folder_path=str(load_dir),
        embeddings=embedding_model,
        allow_dangerous_deserialization=True,
    )

    # Log index statistics for operational visibility
    index_size = vector_store.index.ntotal
    logger.info(
        f"FAISS index loaded from {load_dir}: {index_size} vectors indexed."
    )

    return vector_store


def index_exists(index_dir: Optional[Path] = None) -> bool:
    """
    Check whether a saved FAISS index exists on disk.

    Used by run_ingestion.py to skip rebuilding when the index is current.

    Args:
        index_dir: Directory to check. Defaults to settings.FAISS_INDEX_DIR.

    Returns:
        True if both required index files exist, False otherwise.
    """
    check_dir = index_dir or FAISS_INDEX_DIR
    return all(
        (check_dir / filename).exists()
        for filename in [FAISS_INDEX_FILENAME, FAISS_DOCSTORE_FILENAME]
    )
