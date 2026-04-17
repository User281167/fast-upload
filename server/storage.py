import shutil
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import UploadFile

UPLOADS_ROOT = Path("uploads")
TEMP_ROOT = Path(".upload_tmp")
CHUNK_SIZE = 1024 * 1024


class UploadConflictError(Exception):
    pass


@dataclass(slots=True)
class UploadRequest:
    target_dir: str
    upload: UploadFile
    allow_overwrite: bool = False


@dataclass(slots=True)
class UploadResult:
    destination: Path
    archive_name: str
    extracted_files: int


async def save_upload(request: UploadRequest) -> UploadResult:
    archive_name = _validate_archive_name(request.upload.filename)
    target_root = _resolve_target_dir(request.target_dir)
    subdir_name = _archive_stem(archive_name)
    destination = target_root / subdir_name

    if (
        destination.exists()
        and any(destination.iterdir())
        and not request.allow_overwrite
    ):
        raise UploadConflictError(
            f"destination '{destination.as_posix()}' already exists; set allow_overwrite=true to replace it"
        )

    temp_dir = TEMP_ROOT / uuid4().hex
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        temp_archive = temp_dir / archive_name
        await _write_upload_to_disk(request.upload, temp_archive)

        staged_dir = temp_dir / "extract"
        staged_dir.mkdir()
        extracted_files = _extract_archive(temp_archive, staged_dir)
        _replace_destination(staged_dir, destination, request.allow_overwrite)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return UploadResult(
        destination=destination,
        archive_name=archive_name,
        extracted_files=extracted_files,
    )


async def _write_upload_to_disk(upload: UploadFile, destination: Path) -> None:
    with destination.open("wb") as output:
        while chunk := await upload.read(CHUNK_SIZE):
            output.write(chunk)

    await upload.close()


def _extract_archive(archive_path: Path, destination: Path) -> int:
    suffix = archive_path.name.lower()
    extracted_files = 0

    if suffix.endswith(".zip"):
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                extracted_files += _safe_extract_member(destination, member.filename)
                archive.extract(member, destination)

        return extracted_files

    if suffix.endswith(".tar.gz") or suffix.endswith(".tgz"):
        with tarfile.open(archive_path, "r:gz") as archive:
            for member in archive.getmembers():
                extracted_files += _safe_extract_member(destination, member.name)
            archive.extractall(destination, filter="data")
        return extracted_files

    raise ValueError("unsupported archive type; use .zip, .tar.gz, or .tgz")


def _safe_extract_member(root: Path, member_name: str) -> int:
    member_path = PurePosixPath(member_name)

    if member_path.is_absolute():
        raise ValueError("archive contains absolute paths")
    if any(part in {"", ".", ".."} for part in member_path.parts):
        raise ValueError("archive contains unsafe relative paths")

    resolved = (root / Path(*member_path.parts)).resolve()
    root_resolved = root.resolve()

    if not resolved.is_relative_to(root_resolved):
        raise ValueError("archive escapes extraction directory")

    return 0 if member_name.endswith("/") else 1


def _replace_destination(
    source: Path, destination: Path, allow_overwrite: bool
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        if not allow_overwrite:
            raise UploadConflictError(
                f"destination '{destination.as_posix()}' already exists; set allow_overwrite=true to replace it"
            )

        shutil.rmtree(destination)

    shutil.copytree(source, destination)


def _resolve_target_dir(target_dir: str) -> Path:
    target = PurePosixPath(target_dir.strip())

    if not target.parts:
        raise ValueError("target_dir is required")
    if target.is_absolute():
        raise ValueError("target_dir must be relative")
    if any(part in {"", ".", ".."} for part in target.parts):
        raise ValueError("target_dir contains invalid path segments")

    resolved = (UPLOADS_ROOT / Path(*target.parts)).resolve()
    uploads_root = UPLOADS_ROOT.resolve()

    if not resolved.is_relative_to(uploads_root):
        raise ValueError("target_dir escapes uploads root")

    return resolved


def _validate_archive_name(filename: str | None) -> str:
    if not filename:
        raise ValueError("file is required")

    name = Path(filename).name
    lower_name = name.lower()

    if not (
        lower_name.endswith(".zip")
        or lower_name.endswith(".tar.gz")
        or lower_name.endswith(".tgz")
    ):
        raise ValueError("unsupported archive type; use .zip, .tar.gz, or .tgz")

    return name


def _archive_stem(filename: str) -> str:
    lower_name = filename.lower()

    if lower_name.endswith(".tar.gz"):
        return filename[:-7]
    if lower_name.endswith(".tgz"):
        return filename[:-4]
    if lower_name.endswith(".zip"):
        return filename[:-4]

    raise ValueError("unsupported archive type; use .zip, .tar.gz, or .tgz")
