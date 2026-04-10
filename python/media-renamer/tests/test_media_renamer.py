import importlib.util
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "media-renamer.py"
    spec = importlib.util.spec_from_file_location("media_renamer", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- process_file routing tests ---

def test_process_file_image_returns_action_result(monkeypatch, tmp_path):
    m = load_module()
    dummy_path = tmp_path / "photo.jpg"
    dummy_path.write_text("x")

    expected = m.ActionResult(action=m.Action.RENAME, path=dummy_path, new_filename="new.jpg")
    monkeypatch.setattr(m, "file_type", lambda _p: m.MediaType.IMAGE)
    monkeypatch.setattr(m, "rename_photo", lambda _p, _d="": expected)

    result = m.process_file(dummy_path)
    assert result == expected


def test_process_file_video_returns_action_result(monkeypatch, tmp_path):
    m = load_module()
    dummy_path = tmp_path / "video.mp4"
    dummy_path.write_text("x")

    expected = m.ActionResult(action=m.Action.RENAME, path=dummy_path, new_filename="new.mp4")
    monkeypatch.setattr(m, "file_type", lambda _p: m.MediaType.VIDEO)
    monkeypatch.setattr(m, "rename_video", lambda _p, _d="": expected)

    result = m.process_file(dummy_path)
    assert result == expected


def test_process_file_trash_returns_action_result(monkeypatch, tmp_path):
    m = load_module()
    dummy_path = tmp_path / "Thumbs.db"
    dummy_path.write_text("x")

    expected = m.ActionResult(action=m.Action.DELETE, path=dummy_path)
    monkeypatch.setattr(m, "file_type", lambda _p: m.MediaType.TRASH)
    monkeypatch.setattr(m, "delete_file", lambda _p: expected)

    result = m.process_file(dummy_path)
    assert result == expected


def test_process_file_unknown_returns_none(monkeypatch, tmp_path, capsys):
    m = load_module()
    dummy_path = tmp_path / "file.bin"
    dummy_path.write_text("x")

    monkeypatch.setattr(m, "file_type", lambda _p: m.MediaType.UNKNOWN)
    result = m.process_file(dummy_path)

    captured = capsys.readouterr()
    assert result is None
    assert "Unsupported file type" in captured.out


# --- file_type tests ---

def test_file_type_image():
    m = load_module()
    assert m.file_type(Path("photo.jpg")) == m.MediaType.IMAGE
    assert m.file_type(Path("photo.JPEG")) == m.MediaType.IMAGE
    assert m.file_type(Path("photo.png")) == m.MediaType.IMAGE


def test_file_type_video():
    m = load_module()
    assert m.file_type(Path("video.mp4")) == m.MediaType.VIDEO
    assert m.file_type(Path("video.MOV")) == m.MediaType.VIDEO


def test_file_type_trash():
    m = load_module()
    assert m.file_type(Path("Thumbs.db")) == m.MediaType.TRASH
    assert m.file_type(Path(".DS_Store")) == m.MediaType.TRASH
    assert m.file_type(Path("desktop.ini")) == m.MediaType.TRASH


def test_file_type_unknown():
    m = load_module()
    assert m.file_type(Path("notes.txt")) == m.MediaType.UNKNOWN


# --- calculate_date tests ---

def test_calculate_date_prefers_meta():
    m = load_module()
    meta = datetime(2020, 1, 1)
    filename = datetime(2021, 1, 1)
    created = datetime(2022, 1, 1)
    modified = datetime(2019, 1, 1)
    result = m.calculate_date(meta, filename, created, modified)
    assert result == meta


def test_calculate_date_falls_back_to_filename():
    m = load_module()
    filename = datetime(2019, 1, 1)
    created = datetime(2022, 1, 1)
    modified = datetime(2021, 1, 1)
    result = m.calculate_date(None, filename, created, modified)
    assert result == filename


def test_calculate_date_uses_modified_when_older():
    m = load_module()
    created = datetime(2022, 1, 1)
    modified = datetime(2019, 1, 1)
    result = m.calculate_date(None, None, created, modified)
    assert result == modified


def test_calculate_date_uses_created_when_older():
    m = load_module()
    created = datetime(2019, 1, 1)
    modified = datetime(2022, 1, 1)
    result = m.calculate_date(None, None, created, modified)
    assert result == created


# --- get_date_from_filename tests ---

def test_get_date_from_filename_yyyymmdd_hhmmss():
    m = load_module()
    result = m.get_date_from_filename(Path("20230415_093012.jpg"))
    assert result == datetime(2023, 4, 15, 9, 30, 12)


def test_get_date_from_filename_dashed_format():
    m = load_module()
    result = m.get_date_from_filename(Path("2023-04-15_09-30-12.jpg"))
    assert result == datetime(2023, 4, 15, 9, 30, 12)


def test_get_date_from_filename_no_match():
    m = load_module()
    result = m.get_date_from_filename(Path("random_name.jpg"))
    assert result is None


# --- get_device_code tests ---

def test_get_device_code_known():
    m = load_module()
    assert m.get_device_code('Canon PowerShot A60') == 'A60'
    assert m.get_device_code('CanonMVI01') == 'A60'


def test_get_device_code_empty():
    m = load_module()
    assert m.get_device_code('') == ''


def test_get_device_code_unknown(capsys):
    m = load_module()
    result = m.get_device_code('Nikon D3500')
    assert result is None
    assert "WARN" in capsys.readouterr().out


def test_get_device_code_empty_with_custom_default():
    m = load_module()
    assert m.get_device_code('', 'MyDevice') == 'MyDevice'


# --- rename_file tests ---

def test_rename_file_returns_action_when_name_differs(tmp_path):
    m = load_module()
    file_path = tmp_path / "old_name.jpg"
    file_path.write_text("x")
    metadata = m.Metadata(
        filename="old_name.jpg",
        extension=".jpg",
        date=datetime(2023, 4, 15, 9, 30, 12),
        device="CA60",
    )
    result = m.rename_file(file_path, metadata)
    assert result.action == m.Action.RENAME
    assert result.new_filename == "2023-04-15_09-30-12_CA60.jpg"


def test_rename_file_returns_none_when_name_matches(tmp_path):
    m = load_module()
    file_path = tmp_path / "2023-04-15_09-30-12.jpg"
    file_path.write_text("x")
    metadata = m.Metadata(
        filename="2023-04-15_09-30-12.jpg",
        extension=".jpg",
        date=datetime(2023, 4, 15, 9, 30, 12),
        device=None,
    )
    result = m.rename_file(file_path, metadata)
    assert result is None


def test_rename_file_without_device(tmp_path):
    m = load_module()
    file_path = tmp_path / "old.jpg"
    file_path.write_text("x")
    metadata = m.Metadata(
        filename="old.jpg",
        extension=".jpg",
        date=datetime(2023, 4, 15, 9, 30, 12),
        device=None,
    )
    result = m.rename_file(file_path, metadata)
    assert result.new_filename == "2023-04-15_09-30-12.jpg"


def test_rename_file_handles_collision(tmp_path):
    m = load_module()
    file_path = tmp_path / "old.jpg"
    file_path.write_text("x")
    (tmp_path / "2023-04-15_09-30-12_S24.jpg").write_text("x")
    metadata = m.Metadata(
        filename="old.jpg",
        extension=".jpg",
        date=datetime(2023, 4, 15, 9, 30, 12),
        device="S24",
    )
    result = m.rename_file(file_path, metadata)
    assert result.new_filename == "2023-04-15_09-30-12_S24_1.jpg"


def test_rename_file_handles_multiple_collisions(tmp_path):
    m = load_module()
    file_path = tmp_path / "old.jpg"
    file_path.write_text("x")
    (tmp_path / "2023-04-15_09-30-12_S24.jpg").write_text("x")
    (tmp_path / "2023-04-15_09-30-12_S24_1.jpg").write_text("x")
    metadata = m.Metadata(
        filename="old.jpg",
        extension=".jpg",
        date=datetime(2023, 4, 15, 9, 30, 12),
        device="S24",
    )
    result = m.rename_file(file_path, metadata)
    assert result.new_filename == "2023-04-15_09-30-12_S24_2.jpg"


# --- perform_action tests ---

def test_perform_action_draft_prints_rename(capsys):
    m = load_module()
    result = m.ActionResult(action=m.Action.RENAME, path=Path("/tmp/old.jpg"), new_filename="new.jpg")
    assert m.perform_action(result, m.Mode.DRAFT) is True
    assert "Rename" in capsys.readouterr().out


def test_perform_action_draft_prints_delete(capsys):
    m = load_module()
    result = m.ActionResult(action=m.Action.DELETE, path=Path("/tmp/file.db"))
    assert m.perform_action(result, m.Mode.DRAFT) is True
    assert "Delete" in capsys.readouterr().out


def test_perform_action_execute_renames(tmp_path):
    m = load_module()
    file_path = tmp_path / "old.jpg"
    file_path.write_text("x")
    result = m.ActionResult(action=m.Action.RENAME, path=file_path, new_filename="new.jpg")
    assert m.perform_action(result, m.Mode.EXECUTE) is True
    assert not file_path.exists()
    assert (tmp_path / "new.jpg").exists()


def test_perform_action_execute_deletes(tmp_path):
    m = load_module()
    file_path = tmp_path / "Thumbs.db"
    file_path.write_text("x")
    result = m.ActionResult(action=m.Action.DELETE, path=file_path)
    assert m.perform_action(result, m.Mode.EXECUTE) is True
    assert not file_path.exists()


def test_perform_action_none_is_noop():
    m = load_module()
    assert m.perform_action(None, m.Mode.EXECUTE) is True


def test_perform_action_execute_rename_failure(tmp_path):
    m = load_module()
    file_path = tmp_path / "nonexistent.jpg"
    result = m.ActionResult(action=m.Action.RENAME, path=file_path, new_filename="new.jpg")
    assert m.perform_action(result, m.Mode.EXECUTE) is False


def test_perform_action_execute_delete_failure(tmp_path):
    m = load_module()
    file_path = tmp_path / "nonexistent.db"
    result = m.ActionResult(action=m.Action.DELETE, path=file_path)
    assert m.perform_action(result, m.Mode.EXECUTE) is False


# --- process_all_files tests ---

def test_process_all_files_prints_summary(tmp_path, capsys, monkeypatch):
    m = load_module()
    img = Image.new('RGB', (1, 1), color='red')
    img.save(str(tmp_path / "20230415_093012.jpg"))
    (tmp_path / "Thumbs.db").write_text("x")
    (tmp_path / "notes.txt").write_text("x")

    monkeypatch.setattr(m.subprocess, "run", lambda *args, **kwargs: MagicMock(stdout=""))

    m.process_all_files(tmp_path)
    output = capsys.readouterr().out
    assert "Summary:" in output


# --- get_image_metadata tests ---

def test_get_image_metadata_reads_exif():
    m = load_module()
    resource = Path(__file__).resolve().parent / "resources" / "01.jpg"
    metadata = m.get_image_metadata(resource)
    assert metadata.filename == "01.jpg"
    assert metadata.extension == ".jpg"
    assert metadata.date_taken == datetime(2004, 7, 17, 10, 15, 30)
    assert metadata.device == "A60"
    assert metadata.date == datetime(2004, 7, 17, 10, 15, 30)


def test_get_image_metadata_falls_back_to_filename_date(tmp_path):
    m = load_module()
    file_path = tmp_path / "20230415_093012.jpg"
    img = Image.new('RGB', (1, 1), color='red')
    img.save(str(file_path))

    metadata = m.get_image_metadata(file_path)
    assert metadata.date == datetime(2023, 4, 15, 9, 30, 12)


# --- get_video_metadata tests ---

def test_get_video_metadata_no_ffprobe(tmp_path, monkeypatch):
    m = load_module()
    file_path = tmp_path / "20230415_093012.mp4"
    file_path.write_text("fake video")

    mock_result = MagicMock()
    mock_result.stdout = ""
    monkeypatch.setattr(m.subprocess, "run", lambda *args, **kwargs: mock_result)

    metadata = m.get_video_metadata(file_path)
    assert metadata.filename == "20230415_093012.mp4"
    assert metadata.extension == ".mp4"
    assert metadata.date == datetime(2023, 4, 15, 9, 30, 12)


def test_get_video_metadata_with_ffprobe_data(tmp_path, monkeypatch):
    m = load_module()
    file_path = tmp_path / "video.mp4"
    file_path.write_text("fake video")

    mock_result = MagicMock()
    mock_result.stdout = '{"format": {"tags": {"creation_time": "2023-06-01T14:30:00.000000Z", "software": "Canon PowerShot A60"}}}'
    monkeypatch.setattr(m.subprocess, "run", lambda *args, **kwargs: mock_result)

    metadata = m.get_video_metadata(file_path)
    assert metadata.date_taken == datetime(2023, 6, 1, 14, 30, 0)
    assert metadata.device == "A60"
    assert metadata.date == datetime(2023, 6, 1, 14, 30, 0)


def test_get_video_metadata_ffprobe_missing(tmp_path, monkeypatch):
    m = load_module()
    file_path = tmp_path / "20230415_093012.mp4"
    file_path.write_text("fake video")

    def raise_fnf(*args, **kwargs):
        raise FileNotFoundError("ffprobe not found")
    monkeypatch.setattr(m.subprocess, "run", raise_fnf)

    metadata = m.get_video_metadata(file_path)
    assert metadata.date == datetime(2023, 4, 15, 9, 30, 12)