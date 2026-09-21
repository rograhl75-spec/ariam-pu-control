import pytest
from io import BytesIO
from PIL import Image

from src.validators import validate_image_upload, validate_required_columns


def test_validate_required_columns_ok():
    validate_required_columns(["A", "B"], {"A"})


def test_validate_required_columns_raises_for_missing():
    with pytest.raises(ValueError):
        validate_required_columns(["A"], {"A", "B"})


def _png_bytes() -> bytes:
    image = Image.new("RGB", (2, 2), color="white")
    buff = BytesIO()
    image.save(buff, format="PNG")
    return buff.getvalue()


def test_validate_image_upload_ok():
    content = _png_bytes()
    validate_image_upload("foto.png", len(content), content)


def test_validate_image_upload_rejects_extension():
    content = _png_bytes()
    with pytest.raises(ValueError):
        validate_image_upload("foto.txt", len(content), content)


def test_validate_image_upload_rejects_size():
    content = _png_bytes()
    with pytest.raises(ValueError):
        validate_image_upload("foto.png", len(content), content, max_size_bytes=1)


def test_validate_image_upload_rejects_invalid_content():
    with pytest.raises(ValueError):
        validate_image_upload("foto.png", 20, b"not-an-image")
