from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image

import media_renamer


# --- process_file routing tests ---

def test_process_file_image_returns_action_result(monkeypatch, tmp_path):
    dummy_path = tmp_path / "photo.jpg"
    dummy_path.write_text("x")

    expected = media_renamer.ActionResult(action=media_renamer.Action.RENAME, path=dummy_path, new_filename="new.jpg")
    monkeypatch.setattr(media_renamer, "file_type", lambda _p: media_renamer.MediaType.IMAGE)
    monkeypatch.setattr(media_renamer, "rename_photo", lambda _p, _d="": expected)

    result = media_renamer.process_file(dummy_path)
    assert result == expected


def test_process_file_video_returns_action_result(monkeypatch, tmp_path):
    dummy_path = tmp_path / "video.mp4"
    dummy_path.write_text("x")

    expected = media_renamer.ActionResult(action=media_renamer.Action.RENAME, path=dummy_path, new_filename="new.mp4")
    monkeypatch.setattr(media_renamer, "file_type", lambda _p: media_renamer.MediaType.VIDEO)
    monkeypatch.setattr(media_renamer, "rename_video", lambda _p, _d="": expected)

    result = media_renamer.process_file(dummy_path)
    assert result == expected


def test_process_file_trash_returns_action_result(monkeypatch, tmp_path):
    dummy_path = tmp_path / "Thumbs.db"
    dummy_path.write_text("x")

    expected = media_renamer.ActionResult(action=media_renamer.Action.DELETE, path=dummy_path)
    monkeypatch.setattr(media_renamer, "file_type", lambda _p: media_renamer.MediaType.TRASH)
    monkeypatch.setattr(media_renamer, "delete_file", lambda _p: expected)

    result = media_renamer.process_file(dummy_path)
    assert result == expected


def test_process_file_unknown_returns_none(monkeypatch, tmp_path, capsys):
    dummy_path = tmp_path / "file.bin"
    dummy_path.write_text("x")

    monkeypatch.setattr(media_renamer, "file_type", lambda _p: media_renamer.MediaType.UNKNOWN)
    result = media_renamer.process_file(dummy_path)

    captured = capsys.readouterr()
    assert result is None
    assert "Unsupported file type" in captured.out


# --- file_type tests ---

def test_file_type_image():
    assert media_renamer.file_type(Path("photo.jpg")) == media_renamer.MediaType.IMAGE
    assert media_renamer.file_type(Path("photo.JPEG")) == media_renamer.MediaType.IMAGE
    assert media_renamer.file_type(Path("photo.png")) == media_renamer.MediaType.IMAGE


def test_file_type_video():
    assert media_renamer.file_type(Path("video.mp4")) == media_renamer.MediaType.VIDEO
    assert media_renamer.file_type(Path("video.MOV")) == media_renamer.MediaType.VIDEO


def test_file_type_trash():
    assert media_renamer.file_type(Path("Thumbs.db")) == media_renamer.MediaType.TRASH
    assert media_renamer.file_type(Path(".DS_Store")) == media_renamer.MediaType.TRASH
    assert media_renamer.file_type(Path("desktop.ini")) == media_renamer.MediaType.TRASH


def test_file_type_unknown():
    assert media_renamer.file_type(Path("notes.txt")) == media_renamer.MediaType.UNKNOWN


# --- calculate_date tests ---

def test_calculate_date_prefers_meta():
    meta = datetime(2020, 1, 1)
    filename = datetime(2021, 1, 1)
    created = datetime(2022, 1, 1)
    modified = datetime(2019, 1, 1)
    result = media_renamer.calculate_date(meta, filename, created, modified)
    assert result == meta


def test_calculate_date_falls_back_to_filename():
    filename = datetime(2019, 1, 1)
    created = datetime(2022, 1, 1)
    modified = datetime(2021, 1, 1)
    result = media_renamer.calculate_date(None, filename, created, modified)
    assert result == filename


def test_calculate_date_uses_modified_when_older():
    created = datetime(2022, 1, 1)
    modified = datetime(2019, 1, 1)
    result = media_renamer.calculate_date(None, None, created, modified)
    assert result == modified


def test_calculate_date_uses_created_when_older():
    created = datetime(2019, 1, 1)
    modified = datetime(2022, 1, 1)
    result = media_renamer.calculate_date(None, None, created, modified)
    assert result == created


# --- get_date_from_filename tests ---

def test_get_date_from_filename_yyyymmdd_hhmmss():
    result = media_renamer.get_date_from_filename(Path("20230415_093012.jpg"))
    assert result == datetime(2023, 4, 15, 9, 30, 12)


def test_get_date_from_filename_dashed_format():
    result = media_renamer.get_date_from_filename(Path("2023-04-15_09-30-12.jpg"))
    assert result == datetime(2023, 4, 15, 9, 30, 12)


def test_get_date_from_filename_no_match():
    result = media_renamer.get_date_from_filename(Path("random_name.jpg"))
    assert result is None


# --- get_device_code tests ---

def test_get_device_code_known():
    assert media_renamer.get_device_code('Canon PowerShot A60') == 'A60'
    assert media_renamer.get_device_code('CanonMVI01') == 'A60'


def test_get_device_code_empty():
    assert media_renamer.get_device_code('') == ''


def test_get_device_code_unknown(capsys):
    result = media_renamer.get_device_code('Nikon D3500')
    assert result == 'Nikon D3500'
    assert "WARN" in capsys.readouterr().out


def test_get_device_code_empty_with_custom_default():
    assert media_renamer.get_device_code('', 'MyDevice') == 'MyDevice'


# --- rename_file tests ---

def test_rename_file_returns_action_when_name_differs(tmp_path):
    file_path = tmp_path / "old_name.jpg"
    file_path.write_text("x")
    metadata = media_renamer.Metadata(
        filename="old_name.jpg",
        extension=".jpg",
        date=datetime(2023, 4, 15, 9, 30, 12),
        device="CA60",
    )
    result = media_renamer.rename_file(file_path, metadata)
    assert result is not None
    assert result.action == media_renamer.Action.RENAME
    assert result.new_filename == "2023-04-15_09-30-12_CA60.jpg"


def test_rename_file_returns_none_when_name_matches(tmp_path):
    file_path = tmp_path / "2023-04-15_09-30-12.jpg"
    file_path.write_text("x")
    metadata = media_renamer.Metadata(
        filename="2023-04-15_09-30-12.jpg",
        extension=".jpg",
        date=datetime(2023, 4, 15, 9, 30, 12),
        device=None,
    )
    result = media_renamer.rename_file(file_path, metadata)
    assert result is None


def test_rename_file_without_device(tmp_path):
    file_path = tmp_path / "old.jpg"
    file_path.write_text("x")
    metadata = media_renamer.Metadata(
        filename="old.jpg",
        extension=".jpg",
        date=datetime(2023, 4, 15, 9, 30, 12),
        device=None,
    )
    result = media_renamer.rename_file(file_path, metadata)
    assert result is not None
    assert result.new_filename == "2023-04-15_09-30-12.jpg"


def test_rename_file_handles_collision(tmp_path):
    file_path = tmp_path / "old.jpg"
    file_path.write_text("x")
    (tmp_path / "2023-04-15_09-30-12_S24.jpg").write_text("x")
    metadata = media_renamer.Metadata(
        filename="old.jpg",
        extension=".jpg",
        date=datetime(2023, 4, 15, 9, 30, 12),
        device="S24",
    )
    result = media_renamer.rename_file(file_path, metadata)
    assert result is not None
    assert result.new_filename == "2023-04-15_09-30-12_S24_1.jpg"


def test_rename_file_handles_multiple_collisions(tmp_path):
    file_path = tmp_path / "old.jpg"
    file_path.write_text("x")
    (tmp_path / "2023-04-15_09-30-12_S24.jpg").write_text("x")
    (tmp_path / "2023-04-15_09-30-12_S24_1.jpg").write_text("x")
    metadata = media_renamer.Metadata(
        filename="old.jpg",
        extension=".jpg",
        date=datetime(2023, 4, 15, 9, 30, 12),
        device="S24",
    )
    result = media_renamer.rename_file(file_path, metadata)
    assert result is not None
    assert result.new_filename == "2023-04-15_09-30-12_S24_2.jpg"


# --- perform_action tests ---

def test_perform_action_draft_prints_rename(capsys):
    result = media_renamer.ActionResult(action=media_renamer.Action.RENAME, path=Path("/tmp/old.jpg"), new_filename="new.jpg")
    assert media_renamer.perform_action(result, media_renamer.Mode.DRAFT) is True
    assert "Rename" in capsys.readouterr().out


def test_perform_action_draft_prints_delete(capsys):
    result = media_renamer.ActionResult(action=media_renamer.Action.DELETE, path=Path("/tmp/file.db"))
    assert media_renamer.perform_action(result, media_renamer.Mode.DRAFT) is True
    assert "Delete" in capsys.readouterr().out


def test_perform_action_execute_renames(tmp_path):
    file_path = tmp_path / "old.jpg"
    file_path.write_text("x")
    result = media_renamer.ActionResult(action=media_renamer.Action.RENAME, path=file_path, new_filename="new.jpg")
    assert media_renamer.perform_action(result, media_renamer.Mode.EXECUTE) is True
    assert not file_path.exists()
    assert (tmp_path / "new.jpg").exists()


def test_perform_action_execute_deletes(tmp_path):
    file_path = tmp_path / "Thumbs.db"
    file_path.write_text("x")
    result = media_renamer.ActionResult(action=media_renamer.Action.DELETE, path=file_path)
    assert media_renamer.perform_action(result, media_renamer.Mode.EXECUTE) is True
    assert not file_path.exists()


def test_perform_action_none_is_noop():
    assert media_renamer.perform_action(None, media_renamer.Mode.EXECUTE) is True


def test_perform_action_execute_rename_failure(tmp_path):
    file_path = tmp_path / "nonexistent.jpg"
    result = media_renamer.ActionResult(action=media_renamer.Action.RENAME, path=file_path, new_filename="new.jpg")
    assert media_renamer.perform_action(result, media_renamer.Mode.EXECUTE) is False


def test_perform_action_execute_delete_failure(tmp_path):
    file_path = tmp_path / "nonexistent.db"
    result = media_renamer.ActionResult(action=media_renamer.Action.DELETE, path=file_path)
    assert media_renamer.perform_action(result, media_renamer.Mode.EXECUTE) is False


# --- process_all_files tests ---

def test_process_all_files_prints_summary(tmp_path, capsys, monkeypatch):
    img = Image.new('RGB', (1, 1), color='red')
    img.save(str(tmp_path / "20230415_093012.jpg"))
    (tmp_path / "Thumbs.db").write_text("x")
    (tmp_path / "notes.txt").write_text("x")

    monkeypatch.setattr(media_renamer.subprocess, "run", lambda *_, **__: MagicMock(stdout=""))

    media_renamer.process_all_files(tmp_path)
    output = capsys.readouterr().out
    assert "Summary:" in output


# --- get_image_metadata tests ---

def test_get_image_metadata_reads_exif(tmp_path):
    file_path = tmp_path / "photo.jpg"
    img = Image.new('RGB', (1, 1), color='red')
    exif = img.getexif()
    exif[0x0110] = "Canon PowerShot A60"      # Model
    exif[0x9003] = "2004:07:17 10:15:30"      # DateTimeOriginal
    img.save(str(file_path), exif=exif.tobytes())

    metadata = media_renamer.get_image_metadata(file_path)
    assert metadata.filename == "photo.jpg"
    assert metadata.extension == ".jpg"
    assert metadata.date_taken == datetime(2004, 7, 17, 10, 15, 30)
    assert metadata.device == "A60"
    assert metadata.date == datetime(2004, 7, 17, 10, 15, 30)


def test_get_image_metadata_falls_back_to_filename_date(tmp_path):
    file_path = tmp_path / "20230415_093012.jpg"
    img = Image.new('RGB', (1, 1), color='red')
    img.save(str(file_path))

    metadata = media_renamer.get_image_metadata(file_path)
    assert metadata.date == datetime(2023, 4, 15, 9, 30, 12)


# --- get_video_metadata tests ---

def test_get_video_metadata_no_ffprobe(tmp_path, monkeypatch):
    file_path = tmp_path / "20230415_093012.mp4"
    file_path.write_text("fake video")

    mock_result = MagicMock()
    mock_result.stdout = ""
    monkeypatch.setattr(media_renamer.subprocess, "run", lambda *_, **__: mock_result)

    metadata = media_renamer.get_video_metadata(file_path)
    assert metadata.filename == "20230415_093012.mp4"
    assert metadata.extension == ".mp4"
    assert metadata.date == datetime(2023, 4, 15, 9, 30, 12)


def test_get_video_metadata_with_ffprobe_data(tmp_path, monkeypatch):
    file_path = tmp_path / "video.mp4"
    file_path.write_text("fake video")

    mock_result = MagicMock()
    mock_result.stdout = '{"format": {"tags": {"creation_time": "2023-06-01T14:30:00.000000Z", "software": "Canon PowerShot A60"}}}'
    monkeypatch.setattr(media_renamer.subprocess, "run", lambda *_, **__: mock_result)

    metadata = media_renamer.get_video_metadata(file_path)
    assert metadata.date_taken == datetime(2023, 6, 1, 14, 30, 0)
    assert metadata.device == "A60"
    assert metadata.date == datetime(2023, 6, 1, 14, 30, 0)


def test_get_video_metadata_ffprobe_missing(tmp_path, monkeypatch):
    file_path = tmp_path / "20230415_093012.mp4"
    file_path.write_text("fake video")

    def raise_fnf(*_, **__):
        raise FileNotFoundError("ffprobe not found")
    monkeypatch.setattr(media_renamer.subprocess, "run", raise_fnf)

    metadata = media_renamer.get_video_metadata(file_path)
    assert metadata.date == datetime(2023, 4, 15, 9, 30, 12)
