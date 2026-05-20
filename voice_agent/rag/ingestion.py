"""
rag/ingestion.py
----------------
End-to-end knowledge base ingestion pipeline.

Design rationale:
  - This module orchestrates the full pipeline: load → chunk → embed → index → save.
  - Called exclusively by run_ingestion.py, not by the live application.
  - Separating ingestion from the app ensures the index is always built from
    a clean state rather than being lazily constructed during user sessions.
"""

from pathlib import Path
from typing import Optional

from langchain_core.documents import Document

from config.settings import KNOWLEDGE_BASE_PATH, FAISS_INDEX_DIR
from rag.chunking import load_knowledge_base, chunk_knowledge_base
from rag.vector_store import build_faiss_index, save_faiss_index, index_exists
from utils.logger import get_logger
from utils.performance import PipelineTimer

logger = get_logger(__name__)


def run_ingestion(
    kb_path: Optional[Path] = None,
    index_dir: Optional[Path] = None,
    force_rebuild: bool = False,
) -> dict:
    """
    Execute the complete knowledge base ingestion pipeline.

    Steps:
    1. Check if index already exists (skip if not force_rebuild).
    2. Load knowledge_base_master.md from disk.
    3. Chunk the document into retrieval-optimised segments.
    4. Build a FAISS index from the embedded chunks.
    5. Persist the index to disk.

    Args:
        kb_path: Override path to knowledge_base_master.md.
        index_dir: Override path to save the FAISS index.
        force_rebuild: If True, rebuild even if index exists.

    Returns:
        Dict with ingestion summary metrics.
    """
    kb_path = kb_path or KNOWLEDGE_BASE_PATH
    index_dir = index_dir or FAISS_INDEX_DIR

    timer = PipelineTimer()
    timer.start_total()

    # Guard: skip rebuild if index exists and force is not requested.
    # This is the primary mechanism that prevents re-embedding on every launch.
    if index_exists(index_dir) and not force_rebuild:
        logger.info(
            f"FAISS index already exists at {index_dir}. "
            f"Skipping ingestion. Use --force to rebuild."
        )
        return {
            "status": "skipped",
            "reason": "Index already exists",
            "index_dir": str(index_dir),
        }

    logger.info("═" * 60)
    logger.info("Starting knowledge base ingestion pipeline")
    logger.info("═" * 60)

    # Stage 1: Load the knowledge base markdown file
    with timer.measure("load"):
        content = load_knowledge_base(kb_path)
        logger.info(f"Loaded: {kb_path.name} ({len(content):,} chars)")

    # Stage 2: Chunk the document into retrieval-optimised segments
    with timer.measure("chunking"):
        documents: list[Document] = chunk_knowledge_base(content=content)
        logger.info(f"Chunking: {len(documents)} chunks created")

    # Stage 3: Build the FAISS index (this triggers embedding generation)
    logger.info("Generating embeddings and building FAISS index...")
    logger.info("(This may take 1–3 minutes on first run — model downloads ~130 MB)")
    with timer.measure("indexing"):
        vector_store = build_faiss_index(documents)

    # Stage 4: Persist the index to disk
    with timer.measure("saving"):
        save_faiss_index(vector_store, index_dir)

    timer.stop_total()
    metrics = timer.get_metrics()

    summary = {
        "status": "success",
        "chunks_created": len(documents),
        "vectors_indexed": vector_store.index.ntotal,
        "index_dir": str(index_dir),
        "timing": {
            "load_sec": round(metrics.retrieval or 0, 2),
            "total_sec": round(metrics.total or 0, 2),
        },
    }

    logger.info("═" * 60)
    logger.info(f"Ingestion complete: {summary['chunks_created']} chunks, "
                f"{summary['vectors_indexed']} vectors")
    logger.info(f"Index saved to: {summary['index_dir']}")
    logger.info("═" * 60)

    return summary
