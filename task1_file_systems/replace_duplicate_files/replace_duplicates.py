"""
Python 3.8 only.

Searches for files with the same content and replaces them with hardlinks.
Accepts path to search in.
"""
import argparse
import hashlib
import os
from pathlib import Path


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("path", default=".", help="Path to search in")


def get_md5(path: Path) -> str:
    """Calculate md5 hash."""
    with open(path) as f:
        return hashlib.md5(f.read().encode()).hexdigest()


def handle_file(file_path: Path, stored_files: dict):
    """
    Store file if it is the first occurrence of this file.
    Unlink and create a new hard link if a file with same md5 already exists.
    """
    md5 = get_md5(file_path)
    if md5 not in stored_files.keys():
        # File first occurrence. Store.
        stored_files[md5] = file_path
        print(f"Stored {file_path} with {md5=}")
    elif file_path.is_symlink():
        # Found symlink. Do nothing.
        print(f"Found symlink {file_path}")
        return
    elif (ino := file_path.stat().st_ino) == stored_files[md5].stat().st_ino:
        # Found hardlink. Do nothing.
        print(f"Found hard link {file_path} to {ino=} with {md5=}")
        return
    else:
        # Same content. Replace with hard link.
        file_path.unlink()
        stored_files[md5].link_to(file_path)
        print(f"Created new hard link {file_path} to a file with {md5=}")


def handle_duplicates(path: str):
    """Replace duplicate files with hard links."""
    stored_files = {}
    for root, _, files in os.walk(path):
        for name in files:
            file_path = Path(root).joinpath(name)
            handle_file(file_path, stored_files)


if __name__ == "__main__":
    args = parser.parse_args()
    handle_duplicates(args.path)
