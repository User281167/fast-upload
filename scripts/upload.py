from __future__ import annotations

import argparse
import tarfile
import tempfile
import zipfile
from pathlib import Path

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compress folder/file and upload to fast-upload server."
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Path to file or folder to compress and upload.",
    )
    parser.add_argument(
        "--target-dir",
        required=True,
        help="Relative destination under uploads/ on server.",
    )
    parser.add_argument(
        "--server",
        default="http://127.0.0.1:8000",
        help="Base server URL.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing existing extracted directory.",
    )
    parser.add_argument(
        "--format",
        choices=("zip", "tar.gz"),
        default="zip",
        help="Archive format to create before upload.",
    )

    return parser.parse_args()


def build_archive(source: Path, temp_dir: Path, archive_format: str) -> Path:
    base_name = source.name

    if archive_format == "zip":
        archive_path = temp_dir / f"{base_name}.zip"

        with zipfile.ZipFile(
            archive_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            if not source.is_dir():
                for path in source.rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(source.parent))
            else:
                archive.write(source, arcname=source.name)

        return archive_path

    archive_path = temp_dir / f"{base_name}.tar.gz"

    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(source, arcname=source.name)

    return archive_path


def run(
    source: Path,
    server: str = "localhost:8000",
    format: str = "zip",
    target_dir: str = "uploads",
    overwrite: bool = False,
) -> None:
    if not source.exists():
        raise SystemExit(f"source not found: {source}")
    if not source.is_dir():
        raise SystemExit(f"source is not a folder: {source}")

    with tempfile.TemporaryDirectory() as temp_dir:
        archive = build_archive(source, Path(temp_dir), format)

        with archive.open("rb") as file_handle:
            response = requests.post(
                f"{server.rstrip('/')}/upload",
                data={
                    "target_dir": target_dir,
                    "allow_overwrite": str(overwrite).lower(),
                },
                files={"file": (archive.name, file_handle, "application/octet-stream")},
                timeout=120,
            )

    print(f"status={response.status_code}")

    try:
        print(response.json())
    except ValueError:
        print(response.text)

    response.raise_for_status()


def main() -> None:
    args = parse_args()
    source = args.source.resolve()

    run(
        source=source,
        server=args.server,
        format=args.format,
        target_dir=args.target_dir,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
