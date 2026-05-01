from typing import Iterable


def format_retrieval_context(entries: Iterable[dict[str, str]]) -> str:
    """Format Qdrant Q&A entries into a plain-text context block for the LLM.

    Each entry is rendered as two lines:
        Q: <question>
        A: <answer>

    Entries are separated by a blank line for readability in the prompt.
    Returns an empty string if no entries are provided.
    """
    blocks: list[str] = []
    for entry in entries:
        blocks.append(f"Q: {entry['question']}\nA: {entry['answer']}")
    return "\n\n".join(blocks)
