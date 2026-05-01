from app.services.retrieval_seed import build_seed_points, point_id_for_question


def test_point_id_is_deterministic_for_same_question():
    assert point_id_for_question("Refund policy?") == point_id_for_question("Refund policy?")


def test_point_id_differs_for_different_questions():
    assert point_id_for_question("a") != point_id_for_question("b")


def test_seed_points_are_idempotent_per_question_order():
    entries = [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}]
    vectors = [[0.0, 0.0], [1.0, 1.0]]
    pts1 = build_seed_points(entries, vectors)
    pts2 = build_seed_points(entries, vectors)
    assert [p["id"] for p in pts1] == [p["id"] for p in pts2]
    assert pts1[0]["payload"]["question"] == "Q1"
    assert pts1[1]["payload"]["answer"] == "A2"
