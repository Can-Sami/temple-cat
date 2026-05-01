from app.services.retrieval_seed import build_seed_points, point_id_for_question


def test_point_id_is_deterministic_for_same_question():
    assert point_id_for_question("Refund policy?") == point_id_for_question("Refund policy?")


def test_build_seed_points_is_stable_for_same_entries():
    entries = [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}]
    vectors = [[0.0, 0.0], [1.0, 1.0]]
    pts1 = build_seed_points(entries=entries, vectors=vectors)
    pts2 = build_seed_points(entries=entries, vectors=vectors)
    assert [p["id"] for p in pts1] == [p["id"] for p in pts2]

