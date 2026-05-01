from app.services.retrieval_runtime import build_help_center_context_block


def test_help_center_context_block_is_delimited():
    entries = [{"question": "What is the refund policy?", "answer": "30 days."}]
    block = build_help_center_context_block(entries)
    assert "Help Center Context" in block
    assert "-----" in block
    assert "Q:" in block and "A:" in block


def test_help_center_context_block_empty_entries_returns_empty():
    assert build_help_center_context_block([]) == ""

