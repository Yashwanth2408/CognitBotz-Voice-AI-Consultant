"""
run_ingestion.py
----------------
Command-line utility to run the knowledge base ingestion pipeline.

Design rationale:
  - Accessible from the command line for indexing.
  - Automatically copies knowledge_base_master.md from workspace root to data/ if needed.
  - Supports force rebuild command-line arguments.
"""

import sys
import warnings
import argparse
import shutil
from pathlib import Path

# Suppress all deprecation, future, and user warnings to keep CLI outputs clean
warnings.filterwarnings("ignore")

# Add voice_agent folder to path so config and rag imports resolve correctly
_current_dir = Path(__file__).parent
sys.path.insert(0, str(_current_dir))

from config.settings import KNOWLEDGE_BASE_PATH, FAISS_INDEX_DIR
from rag.ingestion import run_ingestion
from utils.logger import get_logger

logger = get_logger("run_ingestion")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest the CognitBotz knowledge base into the FAISS vector index."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild the FAISS index even if it already exists.",
    )
    args = parser.parse_args()

    # Step 1: Locate the source knowledge_base_master.md.
    # It might be in the parent directory (project root) or in the data/ directory.
    project_root = _current_dir.parent
    source_kb = project_root / "knowledge_base_master.md"

    # Ensure the destination data/ directory exists
    KNOWLEDGE_BASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not KNOWLEDGE_BASE_PATH.exists():
        if source_kb.exists():
            logger.info(f"Copying knowledge base from {source_kb} to {KNOWLEDGE_BASE_PATH}")
            shutil.copy2(source_kb, KNOWLEDGE_BASE_PATH)
        else:
            logger.error(
                f"Knowledge base file not found at {KNOWLEDGE_BASE_PATH} or {source_kb}.\n"
                f"Please ensure knowledge_base_master.md is in your project directory."
            )
            sys.exit(1)

    # Step 2: Run the ingestion pipeline
    try:
        summary = run_ingestion(
            kb_path=KNOWLEDGE_BASE_PATH,
            index_dir=FAISS_INDEX_DIR,
            force_rebuild=args.force,
        )

        if summary.get("status") == "success":
            logger.info("Ingestion completed successfully.")
            logger.info(f"Chunks created: {summary.get('chunks_created')}")
            logger.info(f"Vectors indexed: {summary.get('vectors_indexed')}")
        else:
            logger.info(f"Ingestion skipped: {summary.get('reason')}")

    except Exception as exc:
        logger.error(f"Ingestion process failed: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
