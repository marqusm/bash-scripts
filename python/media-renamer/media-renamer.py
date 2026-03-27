import argparse
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
import os
import subprocess
import json

# Constants
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
FILENAME_FORMAT = "%Y-%m-%d_%H-%M-%S"
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm'}
mode = None


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
    filename: str = None
    extension: str = None
    suffix: str = None
    height: int = None
    width: int = None
    date_taken: datetime = None
    date_filename: datetime | None = None
    date_attr_created: datetime = None
    date_attr_modified: datetime = None
    date: datetime = None
    format: str | None = None
    device: str = None

@dataclass
class ActionResult:
    action: Action
    path: Path
    new_filename: str | None = None


# Functions
def main():
    global mode
    start_time = datetime.now()
    print(f"Starting script: {start_time.strftime(DATETIME_FORMAT)}")
    args = parse_arguments()
    print(f"Args: {args}")
    mode = Mode.EXECUTE if args.execute else Mode.DRAFT
    folder_path = get_folder_path(args.path)
    process_all_files(folder_path)
    elapsed = datetime.now() - start_time
    print(f"Script finished successfully in {elapsed.total_seconds():.1f}s")


def get_folder_path(folder_path):
    folder_path = Path(folder_path)
    if not folder_path.exists() or not folder_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {folder_path}")
    return folder_path

def process_all_files(folder_path):
    for file in folder_path.iterdir():
        if file.is_file():
            action = process_file(file)
            perform_action(action)
    # Optional: recursive processing
    # for file in directory.rglob("*"):
    #     if file.is_file():
    #         process_file(file)

def process_file(file_path) -> ActionResult | None:
    media_type = file_type(file_path)
    if media_type == MediaType.IMAGE:
        return rename_photo(file_path)
    elif media_type == MediaType.VIDEO:
        return rename_video(file_path)
    elif media_type == MediaType.TRASH:
        return delete_file(file_path)
    else:
        print(f"Unknown media type: {file_path}")
        return None

# Actions
def delete_file(file_path: Path) -> ActionResult:
    return ActionResult(action=Action.DELETE, path=Path(file_path))

def rename_photo(file_path: Path) -> ActionResult | None:
    metadata = get_image_metadata(file_path)
    return rename_file(file_path, metadata)

def rename_video(file_path: Path) -> ActionResult | None:
    metadata = get_video_metadata(file_path)
    return rename_file(file_path, metadata)

def rename_file(file_path: Path, metadata: Metadata) -> ActionResult | None:
    desired_filename = f"{metadata.date.strftime(FILENAME_FORMAT)}{f'_{metadata.device}' if metadata.device else ''}{metadata.extension}"
    if desired_filename == metadata.filename:
        print(f"Skip: {file_path}")
        return None

    return ActionResult(action=Action.RENAME, path=Path(file_path), new_filename=desired_filename)

def perform_action(result: ActionResult | None):
    if result is None:
        return

    global mode
    if result.action == Action.DELETE:
        if mode == Mode.EXECUTE:
            os.remove(result.path)
        else:
            print(f"Delete: {result.path}")
    elif result.action == Action.RENAME:
        if result.new_filename is None:
            return
        if mode == Mode.EXECUTE:
            new_file = result.path.parent / result.new_filename
            result.path.rename(new_file)
        else:
            print(f"Rename {result.path} -> {result.new_filename}")


# Helper functions
def calculate_date(meta: datetime | None, filename: datetime | None, attr_created: datetime, attr_modified: datetime) -> datetime:
    if meta:
        return meta
    candidates: list[datetime] = [attr_created, attr_modified]
    if filename:
        candidates.append(filename)
    return min(candidates)

def get_date_from_filename(file_path: Path):
    filename = file_path.stem
    date_formats = [
        (re.compile(r".*(\d\d\d\d\d\d\d\d_\d\d\d\d\d\d).*"), "%Y%m%d_%H%M%S"),
        (re.compile(r".*(\d\d\d\d-\d\d-\d\d_\d\d-\d\d-\d\d).*"), "%Y-%m-%d_%H-%M-%S"),
        (re.compile(r".*(\d\d\d\d-\d\d-\d\d \d\d_\d\d_\d\d).*"), "%Y-%m-%d %H_%M_%S"),
    ]
    for pattern, fmt in date_formats:
        if pattern.match(filename):
            date = pattern.findall(filename)[0]
            try:
                return datetime.strptime(date, fmt)
            except ValueError:
                continue
    return None

def get_device_code(device_name):
    if device_name in ['Canon PowerShot A60', 'CanonMVI01']:
        return 'CA60'
    elif device_name == '':
        return ''
    else:
        print(f"WARN: Unknown device name: {device_name}")
        return ''

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
    return parser.parse_args()

def file_type(file_path):
    ext = Path(file_path).suffix.lower()
    name = Path(file_path).name
    if ext in IMAGE_EXTENSIONS:
        return MediaType.IMAGE
    elif ext in VIDEO_EXTENSIONS:
        return MediaType.VIDEO
    elif name == 'Thumbs.db':
        return MediaType.TRASH
    else:
        return MediaType.UNKNOWN

def get_video_metadata(file_path):
    metadata = Metadata()
    metadata.filename = file_path.name
    metadata.extension = file_path.suffix.lower()
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        data = json.loads(result.stdout)
        if 'format' in data and 'tags' in data['format']:
            tags = data['format']['tags']
            if 'creation_time' in tags:
                metadata.date_taken = datetime.strptime(tags['creation_time'], "%Y-%m-%dT%H:%M:%S.%fZ")
            if 'software' in tags:
                metadata.device = get_device_code(tags['software'])
    metadata.date_filename = get_date_from_filename(file_path)
    metadata.date_attr_created = datetime.fromtimestamp(file_path.stat().st_ctime)
    metadata.date_attr_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
    metadata.date = calculate_date(metadata.date_taken, metadata.date_filename, metadata.date_attr_created, metadata.date_attr_modified)
    return metadata

def get_image_metadata(file_path):
    metadata = Metadata()
    metadata.filename = file_path.name
    metadata.extension = file_path.suffix.lower()
    exif_dict = {}
    with Image.open(file_path) as img:
        metadata.width = img.width
        metadata.height = img.height
        metadata.format = img.format
        try:
            exif_data = img.getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_dict[tag] = value
                if 'UserComment' in exif_dict:
                    del exif_dict['UserComment']
                if 'MakerNote' in exif_dict:
                    del exif_dict['MakerNote']
        except Exception as e:
            print(f"Error reading EXIF: {e}")
    if 'DateTimeOriginal' in exif_dict:
        metadata.date_taken = datetime.strptime(exif_dict['DateTimeOriginal'], "%Y:%m:%d %H:%M:%S")
    if 'Model' in exif_dict:
        metadata.device = get_device_code(exif_dict['Model'])
    metadata.date_filename = get_date_from_filename(file_path)
    metadata.date_attr_created = datetime.fromtimestamp(file_path.stat().st_ctime)
    metadata.date_attr_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
    metadata.date = calculate_date(metadata.date_taken, metadata.date_filename, metadata.date_attr_created, metadata.date_attr_modified)
    return metadata


if __name__ == "__main__":
    main()
