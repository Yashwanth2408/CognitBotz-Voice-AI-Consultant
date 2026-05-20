"""
rag/chunking.py
---------------
Intelligent, section-aware chunking of the knowledge_base_master.md document.

Design rationale:
  - Section-aware splitting preserves the semantic context of each chunk.
  - Header metadata (e.g., "SERVICES > IDP > Features") allows precise source attribution.
  - Overlap of 50 tokens ensures continuity across chunk boundaries.
  - RecursiveCharacterTextSplitter is the fallback for text blocks that exceed
    the chunk size after header-based splitting.
"""

import re
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from config.settings import CHUNK_SIZE, CHUNK_OVERLAP, KNOWLEDGE_BASE_PATH
from config.constants import KB_SECTIONS
from utils.logger import get_logger

logger = get_logger(__name__)


# Markdown headers to use as chunk boundaries and metadata keys.
# Corresponds to the heading levels used in knowledge_base_master.md.
_HEADERS_TO_SPLIT_ON: list[tuple[str, str]] = [
    ("#", "section"),
    ("##", "subsection"),
    ("###", "topic"),
    ("####", "subtopic"),
]


def load_knowledge_base(path: Optional[Path] = None) -> str:
    """
    Load the markdown knowledge base from disk.

    Args:
        path: Override path. Defaults to settings.KNOWLEDGE_BASE_PATH.

    Returns:
        Raw markdown content as a string.

    Raises:
        FileNotFoundError: If the knowledge base file does not exist.
    """
    kb_path = path or KNOWLEDGE_BASE_PATH
    if not kb_path.exists():
        raise FileNotFoundError(
            f"Knowledge base not found at: {kb_path}\n"
            f"Ensure data/knowledge_base_master.md exists."
        )

    content = kb_path.read_text(encoding="utf-8")
    logger.info(f"Loaded knowledge base: {kb_path} ({len(content)} chars)")
    return content


def chunk_knowledge_base(
    content: Optional[str] = None,
    path: Optional[Path] = None,
) -> list[Document]:
    """
    Split the knowledge base into retrieval-optimised chunks.

    Two-stage chunking strategy:
    1. MarkdownHeaderTextSplitter: Respects document structure, preserves
       section/subsection/topic as metadata on each chunk.
    2. RecursiveCharacterTextSplitter: Further splits any chunk that still
       exceeds the target chunk size after stage 1.

    Args:
        content: Pre-loaded markdown text. If None, loads from disk.
        path: Override knowledge base path.

    Returns:
        List of LangChain Document objects with section metadata.
    """
    if content is None:
        content = load_knowledge_base(path)

    # Stage 1: Split on markdown headers to preserve document structure
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=_HEADERS_TO_SPLIT_ON,
        strip_headers=False,  # Keep headers in chunk content for context
    )
    header_chunks: list[Document] = header_splitter.split_text(content)
    logger.info(f"Header splitting produced {len(header_chunks)} initial chunks")

    # Stage 2: Further split large chunks with a character-level splitter
    # Separators ordered from most to least disruptive — preserves sentences
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    final_chunks: list[Document] = []
    for doc in header_chunks:
        if len(doc.page_content) <= CHUNK_SIZE:
            # Chunk is already within size limit — use directly
            final_chunks.append(_enrich_metadata(doc))
        else:
            # Split the oversized chunk, carrying forward all metadata
            sub_docs = char_splitter.create_documents(
                texts=[doc.page_content],
                metadatas=[doc.metadata],
            )
            for sub_doc in sub_docs:
                final_chunks.append(_enrich_metadata(sub_doc))

    # Filter out chunks that are effectively empty after stripping whitespace
    final_chunks = [
        doc for doc in final_chunks
        if len(doc.page_content.strip()) > 20
    ]

    logger.info(
        f"Chunking complete: {len(final_chunks)} chunks "
        f"(avg {sum(len(d.page_content) for d in final_chunks) // len(final_chunks)} chars)"
    )

    return final_chunks


def _enrich_metadata(doc: Document) -> Document:
    """
    Add computed metadata fields to a chunk for source attribution in the UI.

    Determines which top-level KB section the chunk belongs to by scanning
    the section/subsection metadata fields against the known KB_SECTIONS list.

    Args:
        doc: LangChain Document with basic header metadata.

    Returns:
        Document with enriched metadata including 'kb_section' and 'display_source'.
    """
    metadata = dict(doc.metadata)

    # Determine the top-level knowledge base section
    combined_headers = " ".join(str(v) for v in metadata.values()).upper()
    kb_section = "General"
    for section in KB_SECTIONS:
        if section.upper() in combined_headers:
            kb_section = section.title()
            break

    metadata["kb_section"] = kb_section

    # Build a human-readable source string for UI display
    parts = []
    if metadata.get("section"):
        parts.append(metadata["section"].strip("# "))
    if metadata.get("subsection"):
        parts.append(metadata["subsection"].strip("# "))
    if metadata.get("topic"):
        parts.append(metadata["topic"].strip("# "))

    metadata["display_source"] = " › ".join(parts) if parts else kb_section

    # Record chunk character length for debugging and quality monitoring
    metadata["chunk_length"] = len(doc.page_content)

    return Document(page_content=doc.page_content, metadata=metadata)
