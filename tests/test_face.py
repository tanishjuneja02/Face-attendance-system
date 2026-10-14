"""Face matching tests use fake embeddings, so no webcam or DeepFace is needed."""
import sys
import types

import numpy as np
import pytest

from core import face


def test_cosine_distance_basics():
    assert face.cosine_distance([1, 0], [1, 0]) == pytest.approx(0.0)
    assert face.cosine_distance([1, 0], [0, 1]) == pytest.approx(1.0)
    assert face.cosine_distance([1, 0], [-1, 0]) == pytest.approx(2.0)


def test_cosine_distance_ignores_vector_length():
    assert face.cosine_distance([2, 0], [1, 0]) == pytest.approx(0.0)


def test_cosine_distance_rejects_zero_vector():
    with pytest.raises(ValueError):
        face.cosine_distance([0, 0], [1, 0])


def test_best_match_is_the_closest_candidate():
    candidates = [
        {"id": 1, "embedding": [0.0, 1.0]},
        {"id": 2, "embedding": [1.0, 0.1]},
        {"id": 3, "embedding": [-1.0, 0.0]},
    ]
    match = face.find_best_match([1.0, 0.0], candidates)
    assert match.student_id == 2
    assert match.distance < 0.01


def test_stranger_is_not_matched():
    candidates = [{"id": 1, "embedding": [0.0, 1.0]}]
    assert face.find_best_match([1.0, 0.0], candidates) is None


def test_threshold_controls_strictness():
    candidates = [{"id": 1, "embedding": [1.0, 0.5]}]  # distance about 0.106
    assert face.find_best_match([1.0, 0.0], candidates, threshold=0.2) is not None
    assert face.find_best_match([1.0, 0.0], candidates, threshold=0.05) is None


def test_no_candidates_or_no_stored_faces():
    assert face.find_best_match([1.0, 0.0], []) is None
    assert face.find_best_match([1.0, 0.0], [{"id": 1, "embedding": None}]) is None


def _fake_deepface(monkeypatch, represent):
    module = types.SimpleNamespace(DeepFace=types.SimpleNamespace(represent=represent))
    monkeypatch.setitem(sys.modules, "deepface", module)


def test_get_embedding_picks_the_largest_face(monkeypatch):
    def represent(**kwargs):
        return [
            {"embedding": [1, 1], "facial_area": {"w": 20, "h": 20}},
            {"embedding": [9, 9], "facial_area": {"w": 80, "h": 90}},
        ]

    _fake_deepface(monkeypatch, represent)
    assert face.get_embedding(np.zeros((10, 10, 3), dtype=np.uint8)) == [9.0, 9.0]


def test_get_embedding_converts_rgb_to_bgr(monkeypatch):
    seen = {}

    def represent(img_path, **kwargs):
        seen["image"] = img_path
        return [{"embedding": [1], "facial_area": {"w": 1, "h": 1}}]

    _fake_deepface(monkeypatch, represent)
    rgb = np.zeros((2, 2, 3), dtype=np.uint8)
    rgb[:, :, 0] = 255  # pure red in RGB
    face.get_embedding(rgb)
    assert seen["image"][0, 0].tolist() == [0, 0, 255]  # red in BGR


def test_get_embedding_without_a_face_raises_with_details(monkeypatch):
    def represent(**kwargs):
        raise ValueError("Face could not be detected.")

    _fake_deepface(monkeypatch, represent)
    with pytest.raises(face.FaceNotFoundError) as info:
        face.get_embedding(np.zeros((10, 10, 3), dtype=np.uint8))
    assert "Face could not be detected." in str(info.value)  # real error is not hidden


def test_get_embedding_falls_back_to_the_next_detector(monkeypatch):
    tried = []

    def represent(detector_backend, **kwargs):
        tried.append(detector_backend)
        if detector_backend == face.DETECTORS[0]:
            raise ValueError("first detector failed")
        return [{"embedding": [5, 5], "facial_area": {"w": 10, "h": 10}}]

    _fake_deepface(monkeypatch, represent)
    if len(face.DETECTORS) < 2:
        return
    assert face.get_embedding(np.zeros((10, 10, 3), dtype=np.uint8)) == [5.0, 5.0]
    assert tried == face.DETECTORS[:2]
