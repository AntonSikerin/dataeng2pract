"""
Python 3.8 only.

Searches for files with the same content and replaces them with hardlinks.
Accepts path to search in.
"""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("path", default=".", help="Path to search in")

FILE_PATH = Path(os.path.abspath(__file__))
PROJECT_PATH = FILE_PATH.parent.parent.parent
TMP_PATH = PROJECT_PATH.joinpath("tmp")
DUPLICATES_PATH = TMP_PATH.joinpath("duplicates.json")


def get_md5(path: Path) -> str:
    """Calculate md5 hash."""
    with open(path) as f:
        return hashlib.md5(f.read().encode()).hexdigest()


def handle_file(file_path: Path, stored_files: dict):
    """
    Skip file if it was checked previously.
    Store file if it is the first occurrence of this file.
    Unlink and create a new hard link if a file with same md5 already exists.
    """
    if file_path.stat().st_mtime <= stored_files['last_check']:
        return
    md5 = get_md5(file_path)
    if md5 not in stored_files.keys():
        # File first occurrence. Store.
        stored_files[md5] = [{'path': file_path.as_posix(), 'st_mtime': file_path.stat().st_mtime}]
        print(f"Stored {file_path} with {md5=}")
        return
    elif file_path.is_symlink():
        # Found symlink. Do nothing.
        print(f"Found symlink {file_path}")
    elif file_path.samefile(stored_files[md5][0]['path']):
        # Found hardlink. Do nothing.
        print(f"Found hard link {file_path} to {file_path.stat().st_ino} with {md5=}")
    else:
        # Same content. Replace with hard link.
        file_path.unlink()
        Path(stored_files[md5][0]['path']).link_to(file_path)
        print(f"Created new hard link {file_path} to a file with {md5=}")
    stored_files[md5].append({'path': file_path.as_posix(), 'st_mtime': file_path.stat().st_mtime})


def read_file() -> dict:
    """Read json file with checked paths. Return template if not exists."""
    if not DUPLICATES_PATH.exists():
        return {'last_check': 0}
    with open(DUPLICATES_PATH) as f:
        return json.load(f)


def store_duplicates(data: dict):
    """Write json file with checked paths."""
    with open(DUPLICATES_PATH, "w") as f:
        json.dump(data, f, indent=2)


def handle_duplicates(path: str, stored_files: dict):
    """Replace duplicate files with hard links."""
    _path = Path(path).expanduser()
    for root, _, files in os.walk(_path):
        for name in files:
            file_path = Path(root).joinpath(name)
            handle_file(file_path, stored_files)


def main(path: str):
    """Read json file. Check duplicates. Store report."""
    new_last_check = time.time()
    stored_files = read_file()
    handle_duplicates(path, stored_files)
    stored_files['last_check'] = new_last_check
    store_duplicates(stored_files)


if __name__ == "__main__":
    main(parser.parse_args().path)
