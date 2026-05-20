"""
rag/source_formatter.py
-----------------------
Formats retrieval result metadata into human-readable source attribution.

Design rationale:
  - Source visibility is a first-class feature per spec section 20 (Feature 7).
  - Users must see exactly which knowledge base sections grounded each response.
  - Clean formatting builds user trust in AI-generated answers.
"""

from rag.retrieval import RetrievalResult
from utils.logger import get_logger

logger = get_logger(__name__)


def format_sources_for_ui(result: RetrievalResult) -> list[dict]:
    """
    Convert a RetrievalResult into a list of UI-displayable source cards.

    Each card contains the source label, relevance score, and a preview
    of the retrieved chunk content.

    Args:
        result: Populated RetrievalResult from KnowledgeRetriever.retrieve().

    Returns:
        List of dicts, each representing one source card for the UI.
        Returns empty list if no results were retrieved.
    """
    if not result.has_results:
        return []

    cards = []
    for i, (doc, score, label) in enumerate(
        zip(result.documents, result.scores, result.source_labels), start=1
    ):
        # Trim the chunk preview to a readable length
        preview = doc.page_content.strip()
        if len(preview) > 200:
            preview = preview[:200].rsplit(" ", 1)[0] + "..."

        cards.append({
            "index": i,
            "source": label,
            "section": doc.metadata.get("kb_section", "Knowledge Base"),
            "score": round(score, 3),
            "score_pct": f"{score * 100:.0f}%",
            "preview": preview,
        })

    return cards


def format_sources_for_log(result: RetrievalResult) -> str:
    """
    Format retrieved sources as a compact log string.

    Args:
        result: Populated RetrievalResult.

    Returns:
        Single-line string listing all source labels and scores.
    """
    if not result.has_results:
        return "No sources retrieved."

    parts = [
        f"[{label} ({score:.2f})]"
        for label, score in zip(result.source_labels, result.scores)
    ]
    return ", ".join(parts)


def format_sources_for_prompt(result: RetrievalResult) -> str:
    """
    Format sources as a brief citation note for injection into the LLM prompt.

    This encourages the LLM to acknowledge its sources in the response.

    Args:
        result: Populated RetrievalResult.

    Returns:
        Formatted source citation text.
    """
    if not result.has_results:
        return ""

    unique_sections = list(dict.fromkeys(result.source_labels))
    return f"Information sourced from: {', '.join(unique_sections[:3])}"
