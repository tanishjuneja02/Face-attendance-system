"""Saving student photos to disk."""
import io
import os
import re
from pathlib import Path

from PIL import Image

from core import database

DB_COPY_MAX_SIDE = 800  # the copy kept in the database is shrunk to save space

PHOTO_DIR = os.environ.get("ATTENDANCE_PHOTO_DIR", "data/photos")


def safe_filename(roll_no):
    """Turn a roll number into a safe file name ('CS/21' -> 'CS_21')."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(roll_no).strip()).strip("_")
    if not cleaned:
        raise ValueError("Roll number has no usable characters for a file name.")
    return cleaned


def photo_path_for(roll_no, photo_dir=None):
    return str(Path(photo_dir or PHOTO_DIR) / f"{safe_filename(roll_no)}.jpg")


def _jpeg_bytes(image_rgb):
    img = Image.fromarray(image_rgb)
    img.thumbnail((DB_COPY_MAX_SIDE, DB_COPY_MAX_SIDE))
    buffer = io.BytesIO()
    img.save(buffer, "JPEG", quality=88)
    return buffer.getvalue()


def save_photo(roll_no, image_rgb, photo_dir=None):
    """Save an RGB numpy image as a JPEG and return its path.

    With the hosted database a copy is also stored there, so the photo survives app restarts.
    """
    path = photo_path_for(roll_no, photo_dir)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image_rgb).save(path, "JPEG")
    if database.using_remote():
        database.save_photo_blob(path, _jpeg_bytes(image_rgb))
    return path


def read_photo_bytes(path):
    """The photo's JPEG bytes from disk, or from the database if the file is gone. None if neither."""
    if not path:
        return None
    if os.path.exists(path):
        with open(path, "rb") as fh:
            return fh.read()
    if database.using_remote():
        return database.get_photo_blob(path)
    return None


def rename_photo(old_path, roll_no, photo_dir=None):
    """Move a photo to the file name of a new roll number and return its path.

    Keeps the old path if there is no photo to move. Without this, a later student
    given the old roll number would overwrite this student's photo.
    """
    new_path = photo_path_for(roll_no, photo_dir)
    if not old_path or os.path.abspath(old_path) == os.path.abspath(new_path):
        return old_path
    moved = False
    if os.path.exists(old_path):
        os.replace(old_path, new_path)
        moved = True
    if database.using_remote() and database.move_photo_blob(old_path, new_path):
        moved = True
    return new_path if moved else old_path


def delete_photo(path):
    if path and os.path.exists(path):
        os.remove(path)
    if path and database.using_remote():
        database.delete_photo_blob(path)