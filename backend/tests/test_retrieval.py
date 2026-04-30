from app.services.retrieval import format_retrieval_context


def test_formats_top_k_entries_for_prompt_context():
    entries = [
        {"question": "refund policy", "answer": "30 days"},
        {"question": "shipping speed", "answer": "2 business days"},
    ]
    ctx = format_retrieval_context(entries)
    assert "Q: refund policy" in ctx
    assert "A: 30 days" in ctx
    assert "Q: shipping speed" in ctx
    assert "A: 2 business days" in ctx


def test_empty_entries_returns_empty_string():
    assert format_retrieval_context([]) == ""


def test_entries_are_separated_by_newlines():
    entries = [{"question": "q1", "answer": "a1"}]
    ctx = format_retrieval_context(entries)
    assert "Q: q1" in ctx
    assert "A: a1" in ctx
    # Q and A must be on separate lines
    lines = ctx.splitlines()
    assert any(line.startswith("Q:") for line in lines)
    assert any(line.startswith("A:") for line in lines)
