"""
rag/retrieval.py
----------------
Semantic retrieval pipeline using FAISS similarity search.

Design rationale:
  - Retrieves the top-K most semantically similar chunks for a given query.
  - Score normalisation converts raw L2 distances to [0,1] similarity scores.
  - Score threshold filtering removes low-confidence chunks that would inject
    irrelevant context into the LLM prompt and increase hallucination risk.
  - Returns both documents and scores for UI transparency.
"""

from dataclasses import dataclass
from typing import Optional

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from config.settings import TOP_K_RETRIEVAL, RETRIEVAL_SCORE_THRESHOLD
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    """
    Structured output from a single retrieval operation.

    Bundles retrieved documents with their similarity scores and
    pre-assembled context text for direct LLM prompt injection.
    """
    documents: list[Document]
    scores: list[float]           # Normalised similarity scores [0, 1]
    context_text: str             # Concatenated chunk text for LLM context
    source_labels: list[str]      # Human-readable source strings for UI display
    query: str                    # Original query (for logging/debugging)

    @property
    def has_results(self) -> bool:
        """True if at least one document was retrieved above the threshold."""
        return len(self.documents) > 0


class KnowledgeRetriever:
    """
    Retrieves relevant knowledge base chunks for user queries.

    Wraps a FAISS vector store to provide scored, filtered, and
    formatted retrieval results suitable for RAG prompt construction.
    """

    def __init__(self, vector_store: FAISS) -> None:
        """
        Initialise the retriever with a loaded FAISS vector store.

        Args:
            vector_store: A populated, loaded FAISS index.
        """
        self._store = vector_store
        logger.info(
            f"KnowledgeRetriever initialised "
            f"(top_k={TOP_K_RETRIEVAL}, threshold={RETRIEVAL_SCORE_THRESHOLD})"
        )

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> RetrievalResult:
        """
        Retrieve the most relevant knowledge base chunks for a query.

        Process:
        1. Embed the query with the BGE query prefix.
        2. Run FAISS similarity search with distance scores.
        3. Normalise L2 distances to similarity scores.
        4. Filter by minimum score threshold.
        5. Assemble context text and source labels.

        Args:
            query: User question or text query.
            top_k: Max chunks to retrieve. Defaults to TOP_K_RETRIEVAL.
            score_threshold: Min score to include. Defaults to RETRIEVAL_SCORE_THRESHOLD.

        Returns:
            RetrievalResult with documents, scores, and assembled context.
        """
        k = top_k or TOP_K_RETRIEVAL
        threshold = score_threshold if score_threshold is not None else RETRIEVAL_SCORE_THRESHOLD

        logger.info(f"Retrieving context for query: '{query[:80]}...' (k={k})")

        try:
            # similarity_search_with_score returns (Document, L2_distance) pairs.
            # Lower L2 distance = higher similarity.
            raw_results: list[tuple[Document, float]] = (
                self._store.similarity_search_with_score(query=query, k=k)
            )
        except Exception as exc:
            logger.error(f"FAISS search failed: {exc}", exc_info=True)
            return RetrievalResult(
                documents=[], scores=[], context_text="",
                source_labels=[], query=query,
            )

        if not raw_results:
            logger.warning("FAISS returned no results for query.")
            return RetrievalResult(
                documents=[], scores=[], context_text="",
                source_labels=[], query=query,
            )

        # Normalise L2 distances to similarity scores.
        # FAISS L2 distances are unbounded; we convert to (0, 1] using:
        # similarity = 1 / (1 + distance)
        # This maps distance=0 → 1.0 (perfect match) and distance→∞ → 0.0.
        raw_distances = [score for _, score in raw_results]
        max_dist = max(raw_distances) if raw_distances else 1.0

        filtered_docs: list[Document] = []
        filtered_scores: list[float] = []

        for doc, distance in raw_results:
            # Normalise to [0, 1] similarity score
            similarity = 1.0 / (1.0 + distance)

            if similarity < threshold:
                logger.debug(
                    f"Excluding chunk (score={similarity:.3f} < threshold={threshold}): "
                    f"{doc.page_content[:60]}..."
                )
                continue

            filtered_docs.append(doc)
            filtered_scores.append(similarity)

        logger.info(
            f"Retrieved {len(filtered_docs)}/{len(raw_results)} chunks "
            f"above threshold {threshold}"
        )

        # Assemble context text by concatenating chunks with source headers.
        # Including source headers in the context helps the LLM cite correctly.
        context_parts: list[str] = []
        source_labels: list[str] = []

        for i, (doc, score) in enumerate(zip(filtered_docs, filtered_scores), start=1):
            source = doc.metadata.get("display_source", "Knowledge Base")
            source_labels.append(source)

            context_parts.append(
                f"[Source {i}: {source}]\n{doc.page_content.strip()}"
            )
            logger.debug(f"  Chunk {i}: score={score:.3f}, source='{source}'")

        context_text = "\n\n".join(context_parts)

        return RetrievalResult(
            documents=filtered_docs,
            scores=filtered_scores,
            context_text=context_text,
            source_labels=source_labels,
            query=query,
        )
