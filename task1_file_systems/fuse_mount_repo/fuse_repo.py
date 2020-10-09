"""
Python 3.8 only.

Usage:
    python fuse_repo.py <REPO_URL> <MOUNT_PATH>
"""
from __future__ import with_statement

import errno
import os
import shutil
import sys
from pathlib import Path
from typing import Tuple

from fuse import FUSE, FuseOSError, Operations

FILE_PATH = Path(os.path.abspath(__file__))
PROJECT_PATH = FILE_PATH.parent.parent.parent
TMP_PATH = PROJECT_PATH.joinpath("tmp")


class Passthrough(Operations):
    def __init__(self, root):
        self.root = root

    # Helpers
    # =======

    def _full_path(self, partial):
        partial = partial.lstrip("/")
        path = os.path.join(self.root, partial)
        return path

    # Filesystem methods
    # ==================

    def access(self, path, mode):
        full_path = self._full_path(path)
        if not os.access(full_path, mode):
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        full_path = self._full_path(path)
        return os.chmod(full_path, mode)

    def chown(self, path, uid, gid):
        full_path = self._full_path(path)
        return os.chown(full_path, uid, gid)

    def getattr(self, path, fh=None):
        full_path = self._full_path(path)
        st = os.lstat(full_path)
        return dict(
            (key, getattr(st, key))
            for key in (
                "st_atime",
                "st_ctime",
                "st_gid",
                "st_mode",
                "st_mtime",
                "st_nlink",
                "st_size",
                "st_uid",
            )
        )

    def readdir(self, path, fh):
        full_path = self._full_path(path)

        dirents = [".", ".."]
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        for r in dirents:
            yield r

    def readlink(self, path):
        pathname = os.readlink(self._full_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def mknod(self, path, mode, dev):
        return os.mknod(self._full_path(path), mode, dev)

    def rmdir(self, path):
        full_path = self._full_path(path)
        return os.rmdir(full_path)

    def mkdir(self, path, mode):
        print("*** mkdir")
        return os.mkdir(self._full_path(path), mode)

    def statfs(self, path):
        full_path = self._full_path(path)
        stv = os.statvfs(full_path)
        return dict(
            (key, getattr(stv, key))
            for key in (
                "f_bavail",
                "f_bfree",
                "f_blocks",
                "f_bsize",
                "f_favail",
                "f_ffree",
                "f_files",
                "f_flag",
                "f_frsize",
                "f_namemax",
            )
        )

    def unlink(self, path):
        return os.unlink(self._full_path(path))

    def symlink(self, name, target):
        return os.symlink(name, self._full_path(target))

    def rename(self, old, new):
        return os.rename(self._full_path(old), self._full_path(new))

    def link(self, target, name):
        return os.link(self._full_path(target), self._full_path(name))

    def utimens(self, path, times=None):
        return os.utime(self._full_path(path), times)

    # File methods
    # ============

    def open(self, path, flags):
        full_path = self._full_path(path)
        return os.open(full_path, flags)

    def create(self, path, mode, fi=None):
        print(f"*** create {path=}")
        full_path = self._full_path(path)
        return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)

    def read(self, path, length, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.write(fh, buf)

    def truncate(self, path, length, fh=None):
        full_path = self._full_path(path)
        with open(full_path, "r+") as f:
            f.truncate(length)

    def flush(self, path, fh):
        return os.fsync(fh)

    def release(self, path, fh):
        return os.close(fh)

    def fsync(self, path, fdatasync, fh):
        return self.flush(path, fh)


def create_if_not_exists(path: Path):
    """Create folder if not exists."""
    if not path.exists():
        path.mkdir(parents=True)


def remove_if_exists(path: Path):
    """Remove path if exists."""
    if path.exists():
        os.system(f'chmod 777 {path} -R')
        shutil.rmtree(path)
        print(f"Removed {path=}")


def make_read_only(path):
    """Make folders and files read only."""
    for root, dirs, files in os.walk(path, topdown=False):
        if root.endswith(".git") or '.git/' in root:
            continue
        for name in files:
            os.chmod(Path(root).joinpath(name), 0o444)
        for name in dirs:
            os.chmod(Path(root).joinpath(name), 0o555)


def print_sep_line():
    print('*'*80)


def clone_repo(root, tmp_repo_path: Path):
    """Clone repository into temp directory."""
    print_sep_line()
    os.chdir(TMP_PATH)
    git_repo = root + ".git"
    os.system(f"git clone {git_repo}")
    print(f"Cloned repo into {tmp_repo_path}")
    print_sep_line()


def get_repo_name(root: str) -> str:
    """Retrieve repo's name from URL."""
    repo_name = root.split("/")[-1]
    print(f"{repo_name=}")
    return repo_name


def prepare_tmp_repo_path(root: str) -> Path:
    """Make path for the temp repo. Clean if exists."""
    repo_name = get_repo_name(root)
    tmp_repo_path = TMP_PATH.joinpath(repo_name)
    remove_if_exists(tmp_repo_path)
    return tmp_repo_path


def prepare_tmp_repo(root) -> Path:
    """Create temp path and clone repo into it."""
    tmp_repo_path = prepare_tmp_repo_path(root)
    clone_repo(root, tmp_repo_path)
    return tmp_repo_path


def resolve_path(path: str, current_path: str) -> Path:
    """Convert path into an absolute path."""
    if path.startswith("/"):
        return Path(path)
    return Path(current_path).joinpath(path)


def prepare_paths(root: str, mount_point: str) -> Tuple[Path, Path]:
    """Prepare paths to be used by FUSE."""
    create_if_not_exists(TMP_PATH)
    mount_path = resolve_path(mount_point, os.getcwd())
    tmp_repo_path = prepare_tmp_repo(root)
    make_read_only(tmp_repo_path)
    return tmp_repo_path, mount_path


def main(root: str, mount_point: str):
    tmp_repo_path, mount_path = prepare_paths(root, mount_point)
    FUSE(
        Passthrough(tmp_repo_path.as_posix()),
        mount_path.as_posix(),
        nothreads=True,
        foreground=True,
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
