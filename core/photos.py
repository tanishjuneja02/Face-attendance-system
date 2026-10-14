"""Saving student photos to disk."""
import os
import re
from pathlib import Path

from PIL import Image

PHOTO_DIR = os.environ.get("ATTENDANCE_PHOTO_DIR", "data/photos")


def safe_filename(roll_no):
    """Turn a roll number into a safe file name ('CS/21' -> 'CS_21')."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(roll_no).strip()).strip("_")
    if not cleaned:
        raise ValueError("Roll number has no usable characters for a file name.")
    return cleaned


def photo_path_for(roll_no, photo_dir=None):
    return str(Path(photo_dir or PHOTO_DIR) / f"{safe_filename(roll_no)}.jpg")


def save_photo(roll_no, image_rgb, photo_dir=None):
    """Save an RGB numpy image as a JPEG and return its path."""
    path = photo_path_for(roll_no, photo_dir)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image_rgb).save(path, "JPEG")
    return path


def rename_photo(old_path, roll_no, photo_dir=None):
    """Move a photo to the file name of a new roll number and return its path.

    Keeps the old path if there is no file to move. Without this, a later student
    given the old roll number would overwrite this student's photo.
    """
    new_path = photo_path_for(roll_no, photo_dir)
    if old_path and os.path.exists(old_path) and os.path.abspath(old_path) != os.path.abspath(new_path):
        os.replace(old_path, new_path)
        return new_path
    return old_path


def delete_photo(path):
    if path and os.path.exists(path):
        os.remove(path)
