from io import BytesIO
import base64
from pathlib import Path
from shutil import copyfile
import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock
from zipfile import ZipFile

from docx import Document
from PIL import Image
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from streamlit.proto.Common_pb2 import FileURLs
from streamlit.runtime.uploaded_file_manager import UploadedFile, UploadedFileRec

from ui import photo_evidence, rear_camera
from ui.photo_evidence import CAMERA_SOURCE, FILE_SOURCE, prepare_photo, select_photos


ROOT = Path(__file__).resolve().parents[1]


def make_upload(name="camera.jpg", fmt="JPEG", color="red"):
    buffer = BytesIO()
    Image.new("RGB", (8, 4), color=color).save(buffer, format=fmt)
    content = buffer.getvalue()
    return UploadedFile(
        UploadedFileRec(file_id=name, name=name, type=Image.MIME[fmt], data=content),
        FileURLs(),
    )


def embedded_photos(document):
    return [
        document.part.related_parts[shape._inline.graphic.graphicData.pic.blipFill.blip.embed].blob
        for shape in document.inline_shapes
    ]


def mock_capture(monkeypatch, capture):
    response = {}

    def component(**kwargs):
        if kwargs["active"] and not response:
            response.update({
                "session": kwargs["session"],
                "status": "photo" if capture else "empty",
                "data": "data:image/jpeg;base64," + base64.b64encode(capture.getvalue()).decode() if capture else None,
            })
        return response or None

    monkeypatch.setattr(rear_camera, "_component", component)


def click(app, label):
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception


def mock_uploads(monkeypatch, uploads, revision=0):
    import streamlit as st

    monkeypatch.setattr(st, "file_uploader", lambda *a, **k: uploads if k["key"].endswith(f"_{revision}") else [])


@pytest.mark.parametrize("fmt, name", [("JPEG", "camera.jpg"), ("PNG", "arquivo.png"), ("WEBP", "foto.webp")])
def test_prepare_photo_normalizes_capture_and_upload(fmt, name):
    upload = make_upload(name, fmt)
    photo = prepare_photo(upload)
    assert photo.name == f"{Path(name).stem}.png"
    with Image.open(BytesIO(photo.content)) as image:
        assert image.format == "PNG"
        assert image.size == (8, 4)
    doc = Document()
    doc.add_picture(BytesIO(photo.content))
    assert len(doc.inline_shapes) == 1


def test_prepare_photo_applies_camera_orientation():
    buffer = BytesIO()
    image = Image.new("RGB", (8, 4))
    exif = image.getexif()
    exif[274] = 6
    image.save(buffer, format="JPEG", exif=exif)
    photo = prepare_photo(SimpleNamespace(name="camera.jpg", getvalue=buffer.getvalue))
    with Image.open(BytesIO(photo.content)) as normalized:
        assert normalized.size == (4, 8)


def test_prepare_photo_preserves_transparent_png_evidence():
    image = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
    image.putpixel((1, 0), (0, 0, 0, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    photo = prepare_photo(SimpleNamespace(name="evidencia.png", getvalue=buffer.getvalue))
    with Image.open(BytesIO(photo.content)) as normalized:
        assert normalized.getpixel((0, 0)) == (0, 0, 0, 0)
        assert normalized.getpixel((1, 0)) == (0, 0, 0, 255)
    document = Document()
    document.add_picture(BytesIO(photo.content))
    assert len(document.inline_shapes) == 1


@pytest.mark.parametrize("content", [b"", b"not-an-image", b"x" * (5 * 1024 * 1024 + 1)])
def test_prepare_photo_rejects_invalid_or_oversized_bytes(content):
    with pytest.raises(ValueError):
        prepare_photo(SimpleNamespace(name="foto.png", getvalue=lambda: content))


def test_prepare_photo_limits_normalized_size(monkeypatch):
    monkeypatch.setattr(photo_evidence, "MAX_PHOTO_BYTES", 10)
    with pytest.raises(ValueError, match="normalizada"):
        prepare_photo(make_upload())


def test_source_switch_never_falls_back_to_other_source():
    upload, capture = make_upload(), make_upload()
    assert select_photos(FILE_SOURCE, [upload], capture) == [upload]
    assert select_photos(CAMERA_SOURCE, [upload], capture) == [capture]
    assert select_photos(CAMERA_SOURCE, [upload], None) == []
    assert select_photos(FILE_SOURCE, [], capture) == []
    assert select_photos(FILE_SOURCE, [], None) == []
    with pytest.raises(ValueError):
        select_photos("invalid", [upload], capture)


def test_render_invalid_active_photo_blocks_save(monkeypatch):
    ui = Mock()
    ui.session_state = {}
    ui.radio.return_value = CAMERA_SOURCE
    ui.file_uploader.return_value = []
    ui.button.side_effect = lambda label, **kwargs: label == "Adicionar evidências à inspeção"
    monkeypatch.setattr(photo_evidence, "render_rear_camera", Mock(side_effect=ValueError("Captura inválida")))
    monkeypatch.setattr(photo_evidence, "st", ui)
    assert photo_evidence.render_photo_evidence("test") is None
    ui.error.assert_called_once()


def test_camera_component_and_uploader_render():
    app = AppTest.from_string(
        "from ui.photo_evidence import render_photo_evidence\n"
        "render_photo_evidence('photo')\n"
    ).run()
    assert not app.exception
    assert len(app.get("component_instance")) == 1
    assert len(app.get("file_uploader")) == 1
    assert CAMERA_SOURCE in app.radio[0].options
    assert not app.get("file_uploader")[0].proto.disabled
    app.radio[0].set_value(CAMERA_SOURCE).run()
    assert not app.exception
    assert app.get("file_uploader")[0].proto.disabled


@pytest.mark.parametrize("source", [FILE_SOURCE, CAMERA_SOURCE])
def test_modular_persists_all_photos_and_report(tmp_path, monkeypatch, source):
    from src.pages import inspecoes

    db_path = tmp_path / "inspections.db"
    monkeypatch.setattr(inspecoes, "get_settings", lambda: SimpleNamespace(db_path=db_path))
    uploads = [make_upload("primeira.jpg"), make_upload("segunda.png", "PNG", "blue")]
    capture = make_upload("camera.jpg")
    mock_uploads(monkeypatch, uploads)
    mock_capture(monkeypatch, capture)
    app = AppTest.from_string("from src.pages.inspecoes import render\nrender()").run()
    app.radio(key="inspecao_source").set_value(source).run()
    click(app, "Adicionar evidências à inspeção")
    selected = uploads if source == FILE_SOURCE else [capture]
    assert len(app.session_state["inspecao_photos"]) == len(selected)
    if source == CAMERA_SOURCE:
        second_capture = make_upload(color="green")
        mock_capture(monkeypatch, second_capture)
        app.run()
        click(app, "Adicionar evidências à inspeção")
        selected.append(second_capture)
        mock_uploads(monkeypatch, [])
    click(app, "Salvar inspeção")
    with sqlite3.connect(db_path) as connection:
        payload = json.loads(connection.execute("SELECT data_json FROM measurements").fetchone()[0])
    assert payload["fotos"] == [prepare_photo(photo).name for photo in selected]
    assert [Path(path).read_bytes() for path in payload["foto_paths"]] == [prepare_photo(photo).content for photo in selected]
    document = Document(BytesIO(app.session_state["inspecao_laudo"]))
    expected = [prepare_photo(photo).content for photo in selected]
    assert embedded_photos(document) == expected
    saved = inspecoes.SQLiteRepository(db_path).list_measurements("inspecao")[0]
    assert saved["foto_paths"] == payload["foto_paths"]
    regenerated = inspecoes.RelatorioService().gerar_relatorio_inspecao(saved["status"], saved["foto_paths"])
    assert embedded_photos(Document(BytesIO(regenerated))) == expected
    assert app.session_state["inspecao_photos"] == []

    next_photos = [make_upload("camera.jpg", color="yellow"), make_upload("camera.jpg", color="blue")]
    app.radio(key="inspecao_source").set_value(FILE_SOURCE).run()
    revision = app.session_state["inspecao_upload_revision"]
    mock_uploads(monkeypatch, next_photos, revision=revision)
    app.run()
    click(app, "Adicionar evidências à inspeção")
    click(app, "Salvar inspeção")
    records = inspecoes.SQLiteRepository(db_path).list_measurements("inspecao")
    assert len(records) == 2
    assert records[1]["foto_paths"] == saved["foto_paths"]
    assert len(set(records[0]["foto_paths"] + records[1]["foto_paths"])) == 4
    assert embedded_photos(Document(BytesIO(app.session_state["inspecao_laudo"]))) == [
        prepare_photo(photo).content for photo in next_photos
    ]
    assert [Path(path).read_bytes() for path in saved["foto_paths"]] == expected
    assert app.session_state["inspecao_photos"] == []


def test_save_keeps_evidence_when_persistence_fails(tmp_path, monkeypatch):
    from src.pages import inspecoes

    monkeypatch.setattr(inspecoes, "get_settings", lambda: SimpleNamespace(db_path=tmp_path / "inspection.db"))
    mock_uploads(monkeypatch, [make_upload(), make_upload(color="blue")])
    app = AppTest.from_string("from src.pages.inspecoes import render\nrender()").run()
    click(app, "Salvar inspeção")
    with sqlite3.connect(tmp_path / "inspection.db") as connection:
        assert connection.execute("SELECT count(*) FROM measurements").fetchone()[0] == 0
    click(app, "Adicionar evidências à inspeção")
    original = list(app.session_state["inspecao_photos"])
    monkeypatch.setattr(inspecoes.SQLiteRepository, "save_measurement", Mock(side_effect=OSError("disco indisponível")))
    next(button for button in app.button if button.label == "Salvar inspeção").click().run()
    assert app.exception
    assert app.session_state["inspecao_photos"] == original


@pytest.mark.parametrize("source", [FILE_SOURCE, CAMERA_SOURCE])
def test_legacy_form_preview_save_and_word(tmp_path, monkeypatch, source):
    import docx
    import requests

    monkeypatch.chdir(tmp_path)
    base = "Relatorio_Processo_Injecao_Atualizado.xlsx"
    copyfile(ROOT / base, tmp_path / base)
    monkeypatch.setattr(requests, "get", lambda *a, **k: SimpleNamespace(
        json=lambda: {"current_weather": {"temperature": 24}}
    ))
    uploads = [make_upload("arquivo.png", "PNG", "blue"), make_upload("segunda.jpg", color="green")]
    capture = make_upload()
    mock_uploads(monkeypatch, uploads)
    mock_capture(monkeypatch, capture)
    documents = []

    def document_factory():
        document = Document()
        documents.append(document)
        return document

    monkeypatch.setattr(docx, "Document", document_factory)
    app = AppTest.from_file(str(ROOT / "app_tablet.py"), default_timeout=20)
    app.session_state["senha_correta"] = True
    app.session_state["menu_ativo"] = "inspecoes"
    app.run()
    assert not app.exception
    next(field for field in app.text_area if field.label == "Observações de Manutenção:").set_value("Mantido na prévia")
    next(field for field in app.text_area if field.label == "Registro Descritivo das Evidências Visuais:").set_value("Todas as fotos do equipamento")
    next(field for field in app.text_area if field.label == "Conclusão Executiva & Recomendações Técnicas:").set_value("Conclusão preservada")
    app.run()
    app.radio(key="foto_insp_source").set_value(source).run()
    assert next(field for field in app.text_area if field.label == "Observações de Manutenção:").value == "Mantido na prévia"
    assert next(field for field in app.text_area if field.label == "Registro Descritivo das Evidências Visuais:").value == "Todas as fotos do equipamento"
    assert next(field for field in app.text_area if field.label == "Conclusão Executiva & Recomendações Técnicas:").value == "Conclusão preservada"
    click(app, "Adicionar evidências à inspeção")
    assert not app.exception
    assert not (tmp_path / "Log_Inspecoes_Semanais.xlsx").exists()
    assert next(field for field in app.text_area if field.label == "Observações de Manutenção:").value == "Mantido na prévia"
    selected = [capture] if source == CAMERA_SOURCE else uploads
    if source == CAMERA_SOURCE:
        second_capture = make_upload(color="yellow")
        mock_capture(monkeypatch, second_capture)
        app.run()
        click(app, "Adicionar evidências à inspeção")
        selected.append(second_capture)
        mock_uploads(monkeypatch, [])
    app.run()
    assert len(app.session_state["foto_insp_photos"]) == 2
    click(app, "Salvar Inspeção e Gerar Laudo Técnico")
    row = pd.read_excel(tmp_path / "Log_Inspecoes_Semanais.xlsx").iloc[0]
    paths = json.loads(row["Foto_Paths"])
    assert len(paths) == 2
    assert row["Foto_Path"] == paths[0]
    assert [(tmp_path / path).read_bytes() for path in paths] == [prepare_photo(photo).content for photo in selected]
    assert row["Manutenção Obs"] == "Mantido na prévia"
    assert row["Evidências Desc"] == "Todas as fotos do equipamento"
    assert row["Conclusão"] == "Conclusão preservada"
    report = BytesIO()
    documents[-1].save(report)
    with ZipFile(report) as archive:
        media = [name for name in archive.namelist() if name.startswith("word/media/")]
        assert len(media) == 2
        assert {archive.read(path) for path in media} == {prepare_photo(photo).content for photo in selected}
    assert len(documents[-1].inline_shapes) == 2
    assert app.session_state["foto_insp_photos"] == []

    # Uma nova inspeção não deve reutilizar as evidências já salvas.
    if source == CAMERA_SOURCE:
        app.radio(key="foto_insp_source").set_value(FILE_SOURCE).run()
    else:
        mock_capture(monkeypatch, None)
        app.radio(key="foto_insp_source").set_value(CAMERA_SOURCE).run()
    click(app, "Salvar Inspeção e Gerar Laudo Técnico")
    rows = pd.read_excel(tmp_path / "Log_Inspecoes_Semanais.xlsx")
    assert len(rows) == 2
    assert pd.isna(rows.iloc[1]["Foto_Path"])
    assert json.loads(rows.iloc[1]["Foto_Paths"]) == []
    assert app.selectbox(key="select_id_insp_banco").value == "INS-002"
    assert embedded_photos(documents[-1]) == []

    # Nomes e conteúdos repetidos não podem sobrescrever nem eliminar anexos.
    if source == FILE_SOURCE:
        app.radio(key="foto_insp_source").set_value(FILE_SOURCE).run()
    selected = [
        make_upload("foto.jpg", color="yellow"),
        make_upload("foto.jpg", color="blue"),
        make_upload("foto.jpg", color="yellow"),
    ]
    revision = app.session_state["foto_insp_upload_revision"]
    mock_uploads(monkeypatch, selected, revision=revision)
    app.run()
    click(app, "Adicionar evidências à inspeção")
    click(app, "Salvar Inspeção e Gerar Laudo Técnico")
    rows = pd.read_excel(tmp_path / "Log_Inspecoes_Semanais.xlsx")
    paths = json.loads(rows.iloc[2]["Foto_Paths"])
    expected = [prepare_photo(photo).content for photo in selected]
    assert len(set(paths + json.loads(rows.iloc[0]["Foto_Paths"]))) == 5
    assert [(tmp_path / path).read_bytes() for path in paths] == expected
    assert rows.iloc[2]["Foto_Path"] == paths[0]
    assert app.selectbox(key="select_id_insp_banco").value == "INS-003"
    assert embedded_photos(documents[-1]) == expected
    assert [p.text for p in documents[-1].paragraphs if p.text.startswith("Evidência ")] == [
        "Evidência 1 de 3", "Evidência 2 de 3", "Evidência 3 de 3",
    ]
    assert any("INS-003" in button.proto.label for button in app.get("download_button"))
    app.run()
    assert embedded_photos(documents[-1]) == expected

    # Um arquivo ausente ou inválido não pode resultar em download parcial.
    unavailable = tmp_path / paths[1]
    content = unavailable.read_bytes()
    for replacement in (None, b"not an image"):
        if replacement is None:
            unavailable.unlink()
        else:
            unavailable.write_bytes(replacement)
        app.run()
        assert not app.exception
        assert any("evidências 2 de 3" in error.value for error in app.error)
        assert not app.get("download_button")
        persisted = pd.read_excel(tmp_path / "Log_Inspecoes_Semanais.xlsx")
        assert json.loads(persisted.iloc[2]["Foto_Paths"]) == paths
    unavailable.write_bytes(content)
    app.run()
    assert not app.error
    assert app.get("download_button")
    assert embedded_photos(documents[-1]) == expected

    # O histórico continua navegável e registros de foto única são preservados.
    app.selectbox(key="select_id_insp_banco").set_value("INS-001").run()
    assert not app.exception
    first_paths = json.loads(rows.iloc[0]["Foto_Paths"])
    assert embedded_photos(documents[-1]) == [(tmp_path / path).read_bytes() for path in first_paths]
    app.run()
    assert app.selectbox(key="select_id_insp_banco").value == "INS-001"
    rows.loc[0, "Foto_Paths"] = float("nan")
    rows.to_excel(tmp_path / "Log_Inspecoes_Semanais.xlsx", index=False)
    app.run()
    assert not app.exception
    assert embedded_photos(documents[-1]) == [(tmp_path / first_paths[0]).read_bytes()]


def test_gallery_accumulates_mixed_sources_removes_and_clears(monkeypatch):
    uploads = [make_upload("primeira.jpg"), make_upload("segunda.jpg", color="blue")]
    mock_uploads(monkeypatch, uploads)
    mock_capture(monkeypatch, make_upload(color="green"))
    app = AppTest.from_string(
        "import streamlit as st\n"
        "from ui.photo_evidence import render_photo_evidence\n"
        "photos = render_photo_evidence('photo')\n"
        "st.session_state['ready'] = photos\n"
        "st.text_area('Descrição')\n"
        "st.text_area('Conclusão')\n"
    ).run()
    app.text_area[0].set_value("Descrição mantida")
    app.text_area[1].set_value("Conclusão mantida")
    app.run()
    assert app.session_state["ready"] is None
    click(app, "Adicionar evidências à inspeção")
    assert len(app.session_state["ready"]) == 2
    app.radio[0].set_value(CAMERA_SOURCE).run()
    click(app, "Adicionar evidências à inspeção")
    assert len(app.session_state["ready"]) == 3
    original = list(app.session_state["ready"])
    app.run()
    app.radio[0].set_value(FILE_SOURCE).run()
    app.radio[0].set_value(CAMERA_SOURCE).run()
    assert app.session_state["ready"] == original
    click(app, "Remover foto 2")
    assert app.session_state["ready"] == [original[0], original[2]]
    app.run()
    assert len(app.session_state["ready"]) == 2
    click(app, "Limpar evidências")
    assert app.session_state["ready"] == []
    app.run()
    assert app.session_state["ready"] == []
    assert app.text_area[0].value == "Descrição mantida"
    assert app.text_area[1].value == "Conclusão mantida"


def test_upload_addition_is_atomic_and_limit_preserves_existing_photos(monkeypatch):
    import streamlit as st

    mock_uploads(monkeypatch, [make_upload(), SimpleNamespace(name="bad.png", getvalue=lambda: b"invalid")])
    app = AppTest.from_string(
        "from ui.photo_evidence import render_photo_evidence\nrender_photo_evidence('photo')"
    ).run()
    click(app, "Adicionar evidências à inspeção")
    assert app.error
    assert app.session_state["photo_photos"] == []
    photos = [prepare_photo(make_upload())] * photo_evidence.MAX_PHOTOS
    app.session_state["photo_photos"] = photos
    monkeypatch.setattr(st, "file_uploader", lambda *a, **k: [make_upload()])
    app.run()
    click(app, "Adicionar evidências à inspeção")
    assert app.error
    assert app.session_state["photo_photos"] == photos
    assert any("Remova fotos" in warning.value for warning in app.warning)


@pytest.mark.parametrize("record, expected", [
    ({"Foto_Path": "antiga.png"}, ["antiga.png"]),
    ({"Foto_Path": float("nan"), "Foto_Paths": float("nan")}, []),
    ({"Foto_Path": "primeira.png", "Foto_Paths": '["primeira.png", "segunda.png"]'}, ["primeira.png", "segunda.png"]),
    ({"Foto_Path": "antiga.png", "Foto_Paths": "[]"}, []),
])
def test_photo_paths_reads_old_and_new_excel_records(record, expected):
    assert photo_evidence.photo_paths(record) == expected


def test_save_photos_does_not_overwrite_same_name(tmp_path):
    photos = [prepare_photo(make_upload()), prepare_photo(make_upload(color="blue"))]
    paths = photo_evidence.save_photos(photos, tmp_path)
    more_paths = photo_evidence.save_photos(photos, tmp_path)
    assert len(set(paths + more_paths)) == 4
    assert [Path(path).read_bytes() for path in paths] == [photo.content for photo in photos]
