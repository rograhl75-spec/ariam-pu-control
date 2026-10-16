import base64
from io import BytesIO
from pathlib import Path
import shutil
import subprocess

from PIL import Image
import pytest

from ui import rear_camera
from ui.photo_evidence import prepare_photo


def payload(content, session=1):
    return {
        "session": session, "status": "photo",
        "data": "data:image/jpeg;base64," + base64.b64encode(content).decode(),
    }


def test_bridge_bytes_use_shared_pipeline():
    content = BytesIO()
    Image.new("RGB", (12, 24), "blue").save(content, format="JPEG")
    upload = rear_camera.decode_capture(payload(content.getvalue()), 1)
    assert upload.name == "camera.jpg"
    assert upload.getvalue() == content.getvalue()
    photo = prepare_photo(upload)
    with Image.open(BytesIO(photo.content)) as image:
        assert image.size == (12, 24)
        assert image.format == "PNG"


@pytest.mark.parametrize("value", [
    None, {"session": 1, "status": "empty"}, payload(b"old", session=0),
])
def test_empty_or_previous_session_never_reuses_capture(value):
    assert rear_camera.decode_capture(value, 1) is None


@pytest.mark.parametrize("value", [
    "invalid", {"session": 1, "status": "error"},
    {"session": 1, "status": "photo", "data": "data:image/png;base64,AAAA"},
    {"session": 1, "status": "photo", "data": "data:image/jpeg;base64,%%%%"},
    payload(b""), payload(b"x" * (rear_camera.MAX_PHOTO_BYTES + 1)),
])
def test_bridge_rejects_malformed_failed_and_oversized_capture(value):
    with pytest.raises(ValueError):
        rear_camera.decode_capture(value, 1)


def test_bridge_invalid_image_rejected_by_shared_validation():
    with pytest.raises(ValueError):
        prepare_photo(rear_camera.decode_capture(payload(b"not an image"), 1))


def test_switching_source_invalidates_camera_but_reruns_keep_current_photo(monkeypatch):
    class State:
        session_state = {}

    monkeypatch.setattr(rear_camera, "st", State)
    response = None
    calls = []

    def component(**kwargs):
        calls.append(kwargs)
        return response

    monkeypatch.setattr(rear_camera, "_component", component)
    assert rear_camera.render_rear_camera("test", True) is None
    response = payload(b"current", session=calls[-1]["session"])
    assert rear_camera.render_rear_camera("test", True).getvalue() == b"current"
    assert rear_camera.render_rear_camera("test", False) is None
    assert rear_camera.render_rear_camera("test", True) is None


@pytest.mark.skipif(shutil.which("node") is None, reason="Node indisponível para testar o navegador simulado")
def test_browser_camera_lifecycle():
    result = subprocess.run(
        ["node", "--test", str(Path(__file__).with_name("rear_camera.test.cjs"))],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
