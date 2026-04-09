import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS

# Constants
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
FILENAME_FORMAT = "%Y-%m-%d_%H-%M-%S"
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm'}
DEVICE_CODES = {
    'Canon PowerShot A60': 'A60',
    'CanonMVI01': 'A60',
    'HMA-L29': 'Mate20',
    'SM-S921B': 'S24',
    'WDY-LX1': 'X6a',
}
DATE_PATTERNS = [
    (re.compile(r"(\d{8}_\d{6})"), "%Y%m%d_%H%M%S"),
    (re.compile(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})"), "%Y-%m-%d_%H-%M-%S"),
    (re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}_\d{2}_\d{2})"), "%Y-%m-%d %H_%M_%S"),
]
TRASH_FILES = {'Thumbs.db', '.DS_Store', 'desktop.ini'}


# Enums
class MediaType(Enum):
    IMAGE = 'image'
    VIDEO = 'video'
    TRASH = 'trash'
    UNKNOWN = 'unknown'

class Mode(Enum):
    DRAFT = 'draft'
    EXECUTE = 'execute'

class Action(Enum):
    DELETE = 'delete'
    RENAME = 'rename'


# Classes
@dataclass
class Metadata:
    filename: str | None = None
    extension: str | None = None
    date_taken: datetime | None = None
    date_filename: datetime | None = None
    date_attr_created: datetime | None = None
    date_attr_modified: datetime | None = None
    date: datetime | None = None
    device: str | None = None

@dataclass
class ActionResult:
    action: Action
    path: Path
    new_filename: str | None = None


# Functions
def main():
    start_time = datetime.now()
    print(f"Starting script: {start_time.strftime(DATETIME_FORMAT)}")
    args = parse_arguments()
    print(f"Args: {args}")
    mode = Mode.EXECUTE if args.execute else Mode.DRAFT
    default_device = args.device
    folder_path = get_folder_path(args.path)
    process_all_files(folder_path, mode, default_device, args.recursive)
    elapsed = datetime.now() - start_time
    print(f"Script finished successfully in {elapsed.total_seconds():.1f}s")


def get_folder_path(folder_path: Path) -> Path:
    if not folder_path.exists() or not folder_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {folder_path}")
    return folder_path

def process_all_files(folder_path: Path, mode: Mode = Mode.DRAFT, default_device: str = "", recursive: bool = False):
    files = folder_path.rglob("*") if recursive else folder_path.iterdir()
    renamed, deleted, skipped, failed = 0, 0, 0, 0
    for file in files:
        if file.is_file():
            action = process_file(file, default_device)
            if action is None:
                skipped += 1
                continue
            if perform_action(action, mode):
                if action.action == Action.RENAME:
                    renamed += 1
                elif action.action == Action.DELETE:
                    deleted += 1
            else:
                failed += 1
    print(f"Summary: {renamed} renamed, {deleted} deleted, {skipped} skipped, {failed} failed")

def process_file(file_path: Path, default_device: str = "") -> ActionResult | None:
    media_type = file_type(file_path)
    if media_type == MediaType.IMAGE:
        return rename_photo(file_path, default_device)
    elif media_type == MediaType.VIDEO:
        return rename_video(file_path, default_device)
    elif media_type == MediaType.TRASH:
        return delete_file(file_path)
    else:
        print(f"Unsupported file type: {file_path}")
        return None

# Actions
def delete_file(file_path: Path) -> ActionResult:
    return ActionResult(action=Action.DELETE, path=file_path)

def rename_photo(file_path: Path, default_device: str = "") -> ActionResult | None:
    metadata = get_image_metadata(file_path, default_device)
    return rename_file(file_path, metadata)

def rename_video(file_path: Path, default_device: str = "") -> ActionResult | None:
    metadata = get_video_metadata(file_path, default_device)
    return rename_file(file_path, metadata)

def rename_file(file_path: Path, metadata: Metadata) -> ActionResult | None:
    base = f"{metadata.date.strftime(FILENAME_FORMAT)}{f'_{metadata.device}' if metadata.device else ''}"
    desired_filename = f"{base}{metadata.extension}"
    if desired_filename == metadata.filename:
        return None

    counter = 1
    while (file_path.parent / desired_filename).exists() and desired_filename != metadata.filename:
        desired_filename = f"{base}_{counter}{metadata.extension}"
        counter += 1

    if desired_filename == metadata.filename:
        return None

    return ActionResult(action=Action.RENAME, path=file_path, new_filename=desired_filename)

def perform_action(result: ActionResult | None, mode: Mode = Mode.DRAFT) -> bool:
    if result is None:
        return True

    if result.action == Action.DELETE:
        print(f"Delete: {result.path}")
        if mode == Mode.EXECUTE:
            try:
                result.path.unlink()
            except OSError as e:
                print(f"WARN: Failed to delete {result.path}: {e}")
                return False
    elif result.action == Action.RENAME:
        if result.new_filename is None:
            return True
        print(f"Rename {result.path} -> {result.new_filename}")
        if mode == Mode.EXECUTE:
            try:
                new_file = result.path.parent / result.new_filename
                result.path.rename(new_file)
            except OSError as e:
                print(f"WARN: Failed to rename {result.path}: {e}")
                return False
    return True


# Helper functions
def is_epoch(dt: datetime) -> bool:
    return dt.year == 1970

def calculate_date(meta: datetime | None, filename: datetime | None, attr_created: datetime, attr_modified: datetime) -> datetime:
    if meta and not is_epoch(meta):
        return meta
    candidates: list[datetime] = []
    if not is_epoch(attr_created):
        candidates.append(attr_created)
    if not is_epoch(attr_modified):
        candidates.append(attr_modified)
    if filename and not is_epoch(filename):
        candidates.append(filename)
    return min(candidates) if candidates else attr_modified

def get_date_from_filename(file_path: Path) -> datetime | None:
    filename = file_path.stem
    for pattern, fmt in DATE_PATTERNS:
        match = pattern.search(filename)
        if match:
            try:
                return datetime.strptime(match.group(1), fmt)
            except ValueError:
                continue
    return None

def get_device_code(device_name: str, default_device: str = "") -> str | None:
    if device_name == '':
        return default_device
    if device_name in DEVICE_CODES:
        return DEVICE_CODES[device_name]
    print(f"WARN: Unknown device name: {device_name}")
    return None

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        type=Path,
        help="Path to the file or directory to process"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--draft", action="store_true", help="Run in draft mode (no changes)")
    group.add_argument("--execute", action="store_true", help="Perform real actions")
    parser.add_argument("--device", type=str, default="", help="Device suffix to use when not available in metadata")
    parser.add_argument("--recursive", action="store_true", help="Process subdirectories recursively")
    return parser.parse_args()

def file_type(file_path: Path) -> MediaType:
    ext = file_path.suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return MediaType.IMAGE
    elif ext in VIDEO_EXTENSIONS:
        return MediaType.VIDEO
    elif file_path.name in TRASH_FILES:
        return MediaType.TRASH
    else:
        return MediaType.UNKNOWN

def get_video_metadata(file_path: Path, default_device: str = "") -> Metadata:
    metadata = Metadata()
    metadata.filename = file_path.name
    metadata.extension = file_path.suffix.lower()
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(file_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print(f"WARN: ffprobe not found, skipping metadata for {file_path.name}")
        metadata.device = default_device
        return resolve_dates(metadata, file_path)
    if result.stdout:
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            print(f"WARN: Invalid ffprobe output for {file_path.name}")
            metadata.device = default_device
            return resolve_dates(metadata, file_path)
        if 'format' in data and 'tags' in data['format']:
            tags = data['format']['tags']
            if 'creation_time' in tags:
                try:
                    metadata.date_taken = datetime.strptime(tags['creation_time'], "%Y-%m-%dT%H:%M:%S.%fZ")
                except ValueError:
                    print(f"WARN: Unexpected creation_time format: {tags['creation_time']}")
            device_name = tags.get('com.android.model') or tags.get('com.apple.quicktime.model') or tags.get('software')
            if device_name:
                metadata.device = get_device_code(device_name, default_device)
            else:
                metadata.device = default_device
    if metadata.device is None:
        metadata.device = default_device
    return resolve_dates(metadata, file_path)

def get_image_metadata(file_path: Path, default_device: str = "") -> Metadata:
    metadata = Metadata()
    metadata.filename = file_path.name
    metadata.extension = file_path.suffix.lower()
    exif_dict = {}
    try:
        with Image.open(file_path) as img:
            try:
                exif_data = img.getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        exif_dict[tag] = value
            except (AttributeError, ValueError, OSError) as e:
                print(f"Error reading EXIF: {e}")
    except Exception as e:
        print(f"WARN: Failed to open image {file_path.name}: {e}")
    if 'DateTimeOriginal' in exif_dict:
        try:
            metadata.date_taken = datetime.strptime(exif_dict['DateTimeOriginal'], "%Y:%m:%d %H:%M:%S")
        except ValueError:
            print(f"WARN: Unexpected DateTimeOriginal format: {exif_dict['DateTimeOriginal']}")
    if 'Model' in exif_dict:
        metadata.device = get_device_code(exif_dict['Model'], default_device)
    else:
        metadata.device = default_device
    return resolve_dates(metadata, file_path)

def resolve_dates(metadata: Metadata, file_path: Path) -> Metadata:
    metadata.date_filename = get_date_from_filename(file_path)
    metadata.date_attr_created = datetime.fromtimestamp(file_path.stat().st_ctime)
    metadata.date_attr_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
    metadata.date = calculate_date(metadata.date_taken, metadata.date_filename, metadata.date_attr_created, metadata.date_attr_modified)
    return metadata


if __name__ == "__main__":
    main()
