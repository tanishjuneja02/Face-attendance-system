"""Tests for camera-independent matching and the merged student page's chart data (no webcam needed)."""
import sys
import types

import numpy as np
import pandas as pd

from core import charts, face


# ----------------------------------------------------------------- matching
def test_student_with_several_embeddings_matches_on_the_closest_one():
    candidates = [{"id": 1, "embedding": [[0.0, 1.0], [1.0, 0.05]]}]  # second one is close
    assert face.find_best_match([1.0, 0.0], candidates).student_id == 1


def test_old_single_embedding_format_still_works():
    candidates = [{"id": 1, "embedding": [1.0, 0.0]}]
    assert face.find_best_match([1.0, 0.0], candidates).student_id == 1
    assert face.is_legacy_embedding([1.0, 0.0])
    assert not face.is_legacy_embedding([[1.0, 0.0]])


def test_two_very_similar_students_are_ambiguous_not_guessed():
    candidates = [{"id": 1, "embedding": [1.0, 0.02]}, {"id": 2, "embedding": [1.0, -0.02]}]
    result = face.match_face([1.0, 0.0], candidates, threshold=0.4, margin=0.04)
    assert result.status == "ambiguous" and result.match is None


def test_clear_winner_is_matched_even_if_runner_up_is_inside_threshold():
    candidates = [{"id": 1, "embedding": [1.0, 0.0]}, {"id": 2, "embedding": [1.0, 0.6]}]
    result = face.match_face([1.0, 0.0], candidates, threshold=0.4, margin=0.04)
    assert result.status == "matched" and result.match.student_id == 1


def test_stranger_is_unknown():
    assert face.match_face([1.0, 0.0], [{"id": 1, "embedding": [0.0, 1.0]}]).status == "unknown"


# ------------------------------------------------------------- image clean-up
def _photo(h, w):
    rng = np.random.default_rng(0)
    return rng.integers(0, 255, (h, w, 3), dtype=np.uint8)


def test_small_and_large_images_end_up_the_same_size_range():
    small = face.prepare_image(_photo(240, 320))
    large = face.prepare_image(_photo(3000, 4000))
    assert max(small.shape[:2]) == face.MIN_SIDE
    assert max(large.shape[:2]) == face.MAX_SIDE
    assert small.dtype == large.dtype == np.uint8 and small.shape[2] == 3


def test_degraded_variants_are_different_images_of_the_same_scene():
    photo = _photo(600, 800)
    variants = face.degraded_variants(photo)
    assert len(variants) == 6
    for v in variants:
        assert v.dtype == np.uint8 and v.ndim == 3 and v.shape[2] == 3
        assert max(v.shape[:2]) <= 480
    assert not np.array_equal(variants[2], variants[3])  # dim vs bright


def test_registration_stores_the_photo_plus_the_copies_where_a_face_is_found(monkeypatch):
    calls = {"n": 0}

    def represent(**kwargs):
        calls["n"] += 1
        if calls["n"] == 3:  # one degraded copy has no face
            raise ValueError("no face")
        return [{"embedding": [float(calls["n"]), 1.0], "facial_area": {"w": 10, "h": 10}}]

    monkeypatch.setitem(sys.modules, "deepface",
                        types.SimpleNamespace(DeepFace=types.SimpleNamespace(represent=represent)))
    embeddings = face.get_registration_embeddings(_photo(300, 400))
    assert len(embeddings) >= 2 and all(isinstance(e, list) for e in embeddings)


# --------------------------------------------------------------- chart data
def _history():
    rows = [
        ("Maths", "2026-10-05", True), ("Maths", "2026-10-06", False), ("Maths", "2026-10-07", True),
        ("Physics", "2026-10-05", True), ("Physics", "2026-10-12", False),
    ]
    return pd.DataFrame(rows, columns=["subject", "date", "present"])


def test_subject_frame_percent_and_status():
    out = charts.subject_frame(_history(), 75).set_index("subject")
    assert out.loc["Maths", "percent"] == 66.7 and out.loc["Maths", "status"] == "low"
    assert out.loc["Physics", "attended"] == 1 and out.loc["Physics", "held"] == 2
    assert list(charts.subject_frame(_history(), 75)["percent"]) == sorted(
        charts.subject_frame(_history(), 75)["percent"])


def test_donut_frame_counts():
    out = charts.donut_frame(_history()).set_index("status")["classes"]
    assert out["Present"] == 3 and out["Absent"] == 2


def test_calendar_frame_one_row_per_day_with_weekday():
    out = charts.calendar_frame(_history())
    assert len(out) == 4
    day = out[out["label"] == "05 Oct 2026"].iloc[0]  # Maths + Physics, both present
    assert day["percent"] == 100 and day["weekday"] == "Mon" and day["held"] == 2
    assert (out["week"].dt.weekday == 0).all()  # weeks start on Monday
