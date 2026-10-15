"""Face embeddings and matching.

Registering a student stores one embedding (a list of numbers describing the
face). Scanning computes a new embedding and finds the closest stored one.
Matching is plain maths on lists, so it can be tested without a camera.
"""
import logging
import os
from dataclasses import dataclass

import cv2
import numpy as np

MODEL_NAME = "Facenet"
DETECTOR = os.environ.get("FACE_DETECTOR", "mtcnn")
# Detectors tried in order. "opencv" needs no download, so it is a safe fallback.
DETECTORS = [DETECTOR] + [d for d in ("opencv",) if d != DETECTOR]
# Cosine distance at or below this counts as the same person (lower = stricter).
# 0.40 is DeepFace's usual value for Facenet. Tune it with real photos.
DEFAULT_THRESHOLD = float(os.environ.get("FACE_THRESHOLD", "0.40"))

# If the two closest students are both inside the threshold and closer to each other than
# this, the scan is "ambiguous" and nobody is marked. Set to 0 to turn it off.
AMBIGUITY_MARGIN = float(os.environ.get("FACE_AMBIGUITY_MARGIN", "0.04"))
# Every photo is resized into this range before the face is read.
MIN_SIDE = 640
MAX_SIDE = 1280

logger = logging.getLogger(__name__)


class FaceNotFoundError(Exception):
    """No face could be found in the image."""


@dataclass
class Match:
    student_id: int
    distance: float



@dataclass
class MatchResult:
    """status is 'matched', 'unknown' (nobody close enough) or 'ambiguous' (two people too close to call)."""
    status: str
    match: "Match | None" = None


def cosine_distance(a, b):
    """0 = same direction (same face), 1 = unrelated, 2 = opposite."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        raise ValueError("Cannot compare an empty (all-zero) embedding.")
    return float(1.0 - np.dot(a, b) / denominator)


def embedding_list(stored):
    """A student's stored face data as a list of embeddings (old single-embedding data still works)."""
    if not stored:
        return []
    if isinstance(stored[0], (list, tuple)):
        return [e for e in stored if e]
    return [stored]


def is_legacy_embedding(stored):
    """True for a student registered with the old single-embedding format."""
    return bool(stored) and not isinstance(stored[0], (list, tuple))


def _student_distances(embedding, candidates):
    """(student_id, best distance over that student's embeddings), closest first."""
    results = []
    for candidate in candidates:
        distances = [cosine_distance(embedding, e) for e in embedding_list(candidate.get("embedding"))]
        if distances:
            results.append((candidate["id"], min(distances)))
    results.sort(key=lambda item: item[1])
    return results


def match_face(embedding, candidates, threshold=DEFAULT_THRESHOLD, margin=None):
    """Decide who a scanned face is. Returns a MatchResult."""
    margin = AMBIGUITY_MARGIN if margin is None else margin
    ranked = _student_distances(embedding, candidates)
    if not ranked or ranked[0][1] > threshold:
        return MatchResult("unknown")
    best_id, best_distance = ranked[0]
    if len(ranked) > 1:
        runner_up = ranked[1][1]
        if runner_up <= threshold and runner_up - best_distance < margin:
            return MatchResult("ambiguous")
    return MatchResult("matched", Match(student_id=best_id, distance=best_distance))


def find_best_match(embedding, candidates, threshold=DEFAULT_THRESHOLD):
    """Return the closest candidate within the threshold, or None (unknown or ambiguous)."""
    return match_face(embedding, candidates, threshold).match


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


def prepare_image(image_rgb):
    """Resize to a standard size and even out the lighting. Input and output are RGB uint8."""
    img = np.ascontiguousarray(np.asarray(image_rgb, dtype=np.uint8))
    height, width = img.shape[:2]
    longest = max(height, width)
    if longest < MIN_SIDE:
        scale, interpolation = MIN_SIDE / longest, cv2.INTER_CUBIC
    elif longest > MAX_SIDE:
        scale, interpolation = MAX_SIDE / longest, cv2.INTER_AREA
    else:
        scale, interpolation = 1.0, cv2.INTER_AREA
    if scale != 1.0:
        img = cv2.resize(img, (round(width * scale), round(height * scale)), interpolation=interpolation)

    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def _shrink(img, longest):
    height, width = img.shape[:2]
    scale = longest / max(height, width)
    if scale >= 1:
        return img
    return cv2.resize(img, (max(1, round(width * scale)), max(1, round(height * scale))),
                      interpolation=cv2.INTER_AREA)


def _jpeg(img_rgb, quality):
    ok, buffer = cv2.imencode(".jpg", img_rgb[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, quality])
    return cv2.imdecode(buffer, cv2.IMREAD_COLOR)[:, :, ::-1].copy() if ok else img_rgb


def _tint(img_rgb, red, green, blue):
    out = img_rgb.astype(np.float32) * np.array([red, green, blue], dtype=np.float32)
    return np.clip(out, 0, 255).astype(np.uint8)


def degraded_variants(image_rgb):
    """Copies of a photo as a worse camera might see it."""
    img = np.ascontiguousarray(np.asarray(image_rgb, dtype=np.uint8))
    medium = _shrink(img, 480)
    return [
        _jpeg(_shrink(img, 320), 40),
        _jpeg(cv2.GaussianBlur(_shrink(img, 200), (0, 0), 1.2), 25),
        np.clip(medium.astype(np.float32) * 0.6, 0, 255).astype(np.uint8),
        np.clip(medium.astype(np.float32) * 1.25 + 30, 0, 255).astype(np.uint8),
        _tint(medium, 1.12, 1.0, 0.88),
        _tint(medium, 0.9, 1.0, 1.12),
    ]


def get_scan_embedding(image_rgb):
    """Embedding for a photo taken at scan time. Tries a few versions of the image."""
    prepared = prepare_image(image_rgb)
    pad = max(prepared.shape[:2]) // 5
    padded = cv2.copyMakeBorder(prepared, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    last_error = None
    for attempt in (prepared, np.asarray(image_rgb), padded):
        try:
            return get_embedding(attempt)
        except FaceNotFoundError as exc:
            last_error = exc
    raise last_error


def get_registration_embeddings(image_rgb):
    """List of embeddings to store for one student: the photo itself + degraded copies."""
    embeddings = [get_scan_embedding(image_rgb)]
    for variant in degraded_variants(image_rgb):
        try:
            embeddings.append(get_scan_embedding(variant))
        except FaceNotFoundError:
            logger.info("Skipped a degraded copy: no face found in it.")
    return embeddings