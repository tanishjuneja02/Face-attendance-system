import numpy as np
import pytest

from core import photos


@pytest.mark.parametrize(
    "roll, expected",
    [("101", "101"), ("CS/21", "CS_21"), (" 7 A ", "7_A"), ("../../etc", "etc")],
)
def test_safe_filename(roll, expected):
    assert photos.safe_filename(roll) == expected


def test_safe_filename_rejects_unusable_roll():
    with pytest.raises(ValueError):
        photos.safe_filename("///")


def test_save_and_delete_photo(tmp_path):
    image = np.full((20, 20, 3), 128, dtype=np.uint8)
    path = photos.save_photo("CS/21", image, photo_dir=tmp_path / "faces")
    assert path.endswith("CS_21.jpg")
    assert (tmp_path / "faces" / "CS_21.jpg").exists()
    photos.delete_photo(path)
    assert not (tmp_path / "faces" / "CS_21.jpg").exists()
    photos.delete_photo(path)  # deleting a missing file is fine
