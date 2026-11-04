"""Safely unpack an uploaded source-code ZIP.

The archive is only read and parsed, never executed. Extraction refuses:
  * entries that escape the destination ("../x", "/etc/x", "C:\\x", "\\\\server\\x")
  * symbolic links
  * archives over the file-count or uncompressed-size limits (zip bombs)
"""
from __future__ import annotations

import stat
import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath


class ArchiveError(ValueError):
    """The upload is not a usable ZIP of source code."""


def safe_extract_zip(data: bytes, dest: Path, max_files: int = 20_000,
                     max_total_bytes: int = 200 * 1024 * 1024) -> Path:
    """Extract ``data`` into ``dest`` and return the repository root.

    If every entry sits under one top-level folder (as in a GitHub "Download ZIP"),
    that folder is returned as the root.
    """
    try:
        archive = zipfile.ZipFile(BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ArchiveError("the uploaded file is not a valid ZIP archive") from exc

    with archive:
        members = [m for m in archive.infolist() if not m.is_dir()]
        if not members:
            raise ArchiveError("the ZIP archive is empty")
        if len(members) > max_files:
            raise ArchiveError(f"the ZIP has {len(members)} files; the limit is {max_files}")
        if sum(m.file_size for m in members) > max_total_bytes:
            raise ArchiveError(f"the ZIP unpacks to more than {max_total_bytes // (1024 * 1024)} MB")

        dest = dest.resolve()
        written = 0
        for m in members:
            rel = _safe_relative(m.filename)
            if stat.S_ISLNK(m.external_attr >> 16):
                raise ArchiveError(f"symbolic links are not allowed: {m.filename}")
            target = (dest / rel).resolve()
            if dest != target and dest not in target.parents:
                raise ArchiveError(f"unsafe path in ZIP: {m.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(m) as src, open(target, "wb") as out:
                # Count real bytes too: header sizes can lie.
                while chunk := src.read(1024 * 1024):
                    written += len(chunk)
                    if written > max_total_bytes:
                        raise ArchiveError(
                            f"the ZIP unpacks to more than {max_total_bytes // (1024 * 1024)} MB")
                    out.write(chunk)

    tops = {PurePosixPath(_safe_relative(m.filename)).parts[0] for m in members}
    if len(tops) == 1 and (dest / next(iter(tops))).is_dir():
        return dest / next(iter(tops))
    return dest


def _safe_relative(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    p = PurePosixPath(normalized)
    absolute = normalized.startswith("/")
    has_drive = bool(p.parts) and ":" in p.parts[0]          # C:/x  or  C:x
    if not p.parts or absolute or has_drive or ".." in p.parts:
        raise ArchiveError(f"unsafe path in ZIP: {name}")
    return p
