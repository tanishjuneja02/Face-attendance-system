"""Face embeddings and matching.

Registering a student stores one embedding (a list of numbers describing the
face). Scanning computes a new embedding and finds the closest stored one.
Matching is plain maths on lists, so it can be tested without a camera.
"""
import logging
import os
from dataclasses import dataclass

import numpy as np

MODEL_NAME = "Facenet"
DETECTOR = os.environ.get("FACE_DETECTOR", "mtcnn")
# Detectors tried in order. "opencv" needs no download, so it is a safe fallback.
DETECTORS = [DETECTOR] + [d for d in ("opencv",) if d != DETECTOR]
# Cosine distance at or below this counts as the same person (lower = stricter).
# 0.40 is DeepFace's usual value for Facenet. Tune it with real photos.
DEFAULT_THRESHOLD = float(os.environ.get("FACE_THRESHOLD", "0.40"))


logger = logging.getLogger(__name__)


class FaceNotFoundError(Exception):
    """No face could be found in the image."""


@dataclass
class Match:
    student_id: int
    distance: float


def cosine_distance(a, b):
    """0 = same direction (same face), 1 = unrelated, 2 = opposite."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        raise ValueError("Cannot compare an empty (all-zero) embedding.")
    return float(1.0 - np.dot(a, b) / denominator)


def find_best_match(embedding, candidates, threshold=DEFAULT_THRESHOLD):
    """Return the closest candidate within the threshold, or None.

    ``candidates`` is a list of dicts with 'id' and 'embedding'.
    """
    best_id, best_distance = None, float("inf")
    for candidate in candidates:
        stored = candidate.get("embedding")
        if not stored:
            continue
        distance = cosine_distance(embedding, stored)
        if distance < best_distance:
            best_id, best_distance = candidate["id"], distance
    if best_id is not None and best_distance <= threshold:
        return Match(student_id=best_id, distance=best_distance)
    return None


def get_embedding(image_rgb):
    """Return the embedding of the largest face in an RGB image (numpy array).

    Each detector in DETECTORS is tried until one finds a face. If none does,
    FaceNotFoundError is raised and includes the underlying error text, so a
    real problem (like a failed model download) is not hidden.

    DeepFace is imported here so the rest of the project (and the tests) load fast.
    """
    from deepface import DeepFace

    bgr = np.ascontiguousarray(np.asarray(image_rgb)[:, :, ::-1])  # DeepFace expects BGR
    last_error = None
    for detector in DETECTORS:
        try:
            faces = DeepFace.represent(
                img_path=bgr,
                model_name=MODEL_NAME,
                detector_backend=detector,
                enforce_detection=True,
            )
        except ValueError as exc:
            logger.warning("Detector '%s' failed: %s", detector, exc)
            last_error = exc
            continue
        if faces:
            largest = max(faces, key=lambda f: f["facial_area"]["w"] * f["facial_area"]["h"])
            return [float(x) for x in largest["embedding"]]

    message = "No face detected. Face the camera in good light."
    if last_error is not None:
        message += f" (Details: {str(last_error)[:300]})"
    raise FaceNotFoundError(message)
