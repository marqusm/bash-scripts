# Media Renamer

## Description

A CLI tool that brings order to messy media libraries by renaming photo and video files into a consistent, date-based naming convention. Instead of dealing with cryptic camera-generated names like `IMG_20230415_093012.jpg` or `DSC_0042.jpg`, every file gets renamed to a uniform `YYYY-MM-DD_HH-MM-SS[_DEVICE].ext` format.

The tool reads the actual creation date from image EXIF data or video metadata (via ffprobe), falling back to filename patterns or file system timestamps when metadata is unavailable. It also identifies and removes junk files like `Thumbs.db`.

## Goals

- **Standardize filenames** across all media files using a consistent date-time format
- **Preserve origin info** by appending a device code (e.g. `CA60` for Canon PowerShot A60) to the filename
- **Use the most accurate date** by prioritizing metadata over filename over file attributes
- **Safe by default** with a `--draft` mode that previews changes before any files are modified
- **Handle mixed media** by supporting both image and video files in a single pass


## Installation

Common Python installation
```python
pip install -r requirements.txt
```

Using Python Launcher
```python
py -m pip install -r requirements.txt
```


## Running
```python
py media-renamer.py
```

| Argument  | Comment      |
|-----------|--------------|
| arg       | Path         |
| -h        | Help         |
| --draft   | Draft mode   |
| --execute | Writing mode |

Example command could be:
```python
py media-renamer.py /home/user/media/photos --execute
```