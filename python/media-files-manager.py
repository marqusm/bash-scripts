import argparse
import re
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
regex_pattern = re.compile("(\d\d\d\d\d\d\d\d_\d\d\d\d\d\d)_?([A-Za-z0-9]*)?_?(.*)?\.(.*)")
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


# Classes
class Metadata:
    filename: str = None
    extension: str = None
    suffix: str = None
    height: int = None
    width: int = None
    date_taken: datetime = None
    date_filename: datetime = None
    date_attr_created: datetime = None
    date_attr_modified: datetime = None
    date: datetime = None
    format: str = None
    device: str = None


# @dataclass
# class Dates:
#     meta_creation: datetime | None
#     file_name: datetime | None
#     file_modified: datetime
#     file_created: datetime


# Functions
def main():
    global mode
    print(f"Starting script: {datetime.now().strftime(DATETIME_FORMAT)}")
    args = parse_arguments()
    print(f"Args: {args}")
    mode = Mode.EXECUTE if args.execute else Mode.DRAFT
    process_all_files(args.path)
    print(f"Script finished successfully: {datetime.now().strftime(DATETIME_FORMAT)}")

    # video_path = Path("example.mp4")
    # meta = get_video_metadata(video_path)
    # duration = float(meta["format"]["duration"])
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # new_name = f"video_{int(duration)}s_{timestamp}{video_path.suffix}"
    # renamed_file = rename_file(video_path, new_name)
    # print(f"Renamed to: {renamed_file}")


# Actions
def rename_file(file_path: str, metadata: Metadata):
    desired_filename = f"{metadata.date.strftime(FILENAME_FORMAT)}{f'_{metadata.device}' if metadata.device else ''}{metadata.extension}"
    global mode
    if desired_filename == metadata.filename:
        print(f"Skip: {file_path}")
        return

    if mode == Mode.EXECUTE:
        file = Path(file_path)
        new_file = file.parent / desired_filename
        file.rename(new_file)
    else:
        print(f"Rename {file_path} -> {desired_filename}")


def delete_file(file_path):
    global mode
    if mode == Mode.EXECUTE:
        os.remove(file_path)
    else:
        print(f"Delete: {file_path}")


# Entity Processors
def process_photo(file_path):
    metadata = get_image_metadata(file_path)
    rename_file(file_path, metadata)


def process_video(file_path):
    metadata = get_video_metadata(file_path)
    rename_file(file_path, metadata)
    # filename = file_path.name
    # extension = file_path.suffix
    # date = calculate_date(
    #     metadata.date_taken,
    #     get_date_from_filename(file_path),
    #     datetime.fromtimestamp(file_path.stat().st_ctime),
    #     datetime.fromtimestamp(file_path.stat().st_mtime),
    # )
    # desired_filename = f"{date[1].strftime(FILENAME_FORMAT)}{metadata.device}{extension}"
    # if filename != desired_filename:
    #     rename_file(file_path, desired_filename)
    # else:
    #     print(f"OK {file_path}")


# Helper functions
def calculate_date(meta: datetime | None, filename: datetime | None, attr_created: datetime, attr_modified: datetime):
    if meta:
        return ['meta', meta]
    elif filename:
        return ['file_name', filename]
    elif attr_modified <= attr_created:
        return ['attr_modified', attr_modified]
    else:
        return ['attr_created', attr_created]


def get_date_from_filename(file_path: Path):
    filename = file_path.stem
    date_formats = [
        [re.compile(r".*(\d\d\d\d\d\d\d\d_\d\d\d\d\d\d).*"), "%Y%m%d_%H%M%S"],
        [re.compile(r".*(\d\d\d\d-\d\d-\d\d_\d\d-\d\d-\d\d).*"), "%Y-%m-%d_%H-%M-%S"],
        [re.compile(r".*(\d\d\d\d-\d\d-\d\d \d\d_\d\d_\d\d).*"), "%Y-%m-%d %H_%M_%S"],
    ]
    for date_format in date_formats:
        if date_format[0].match(filename):
            date = date_format[0].findall(filename)[0][0]
            return datetime.strptime(date, date_format[1])
    return None


def get_device_code(device_name):
    if device_name in ['Canon PowerShot A60', 'CanonMVI01']:
        return 'CA60'
    elif device_name == '':
        return ''
    else:
        print(f"WARN: Unknown device name: {device_name}")
        return ''


def process_file(file_path):
    media_type = file_type(file_path)
    if media_type == MediaType.IMAGE:
        process_photo(file_path)
    elif media_type == MediaType.VIDEO:
        process_video(file_path)
    elif media_type == MediaType.TRASH:
        delete_file(file_path)
    else:
        print("Unknown media type")


def process_all_files(folder_path):
    folder_path = Path(folder_path)
    if not folder_path.exists() or not folder_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {folder_path}")
    for file in folder_path.iterdir():
        if file.is_file():
            process_file(file)
    # Optional: recursive processing
    # for file in directory.rglob("*"):
    #     if file.is_file():
    #         process_file(file)


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
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    metadata = Metadata()
    if 'format' in data and 'tags' in data['format'] and 'creation_time' in data['format']['tags']:
        metadata.date_taken = datetime.strptime(data['format']['tags']['creation_time'], "%Y-%m-%d %H:%M:%S")
    else:
        metadata.date_taken = None
    if 'format' in data and 'tags' in data['format'] and 'software' in data['format']['tags']:
        metadata.device = data['format']['tags']['software']
        metadata.device = get_device_code(metadata.device)
    else:
        metadata.device = None
    return metadata


def get_image_metadata(file_path):
    metadata = Metadata()
    metadata.filename = file_path.stem
    metadata.extension = file_path.suffix.lower()
    with Image.open(file_path) as img:
        metadata.width = img.width
        metadata.height = img.height
        metadata.format = img.format
        try:
            exif_data = img._getexif()
            exif_dict = {}
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
    metadata.date_taken = datetime.strptime(exif_dict['DateTimeOriginal'], "%Y:%m:%d %H:%M:%S")
    metadata.date_taken = datetime.strftime(metadata.date_taken, FILENAME_FORMAT)
    metadata.device = exif_dict['Model']
    metadata.device = get_device_code(metadata.device)
    return metadata


main()
