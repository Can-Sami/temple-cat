from app.services.retrieval_runtime import (
    build_help_center_context_block,
    insert_help_center_system_message,
    strip_help_center_messages,
)


def test_help_center_context_block_contains_header_and_qa():
    entries = [{"question": "What is the refund policy?", "answer": "30 days."}]
    block = build_help_center_context_block(entries)
    assert "Help Center Context" in block
    assert "Q:" in block and "A:" in block
    assert "refund policy" in block.lower()


def test_strip_help_center_removes_only_marked_system_messages():
    msgs = [
        {"role": "system", "content": "You are helpful."},
        {
            "role": "system",
            "content": "### Help Center Context (retrieved; may be incomplete)\n\nQ: Hi\nA: There",
        },
        {"role": "user", "content": "Hello"},
    ]
    stripped = strip_help_center_messages(msgs)
    assert len(stripped) == 2
    assert stripped[0]["role"] == "system"
    assert stripped[1]["role"] == "user"


def test_insert_help_center_places_block_after_first_system():
    base = [
        {"role": "system", "content": "Personality."},
        {"role": "user", "content": "Shipping?"},
    ]
    content = "### Help Center Context (retrieved; may be incomplete)\n\nQ: x\nA: y"
    out = insert_help_center_system_message(base, content)
    assert len(out) == 3
    assert out[0]["role"] == "system" and out[0]["content"] == "Personality."
    assert out[1]["role"] == "system" and "Help Center Context" in out[1]["content"]
    assert out[2]["role"] == "user"
