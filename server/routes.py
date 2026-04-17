from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from server.storage import UploadConflictError, UploadRequest, save_upload

router = APIRouter()


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_archive(
    target_dir: str = Form(...),
    file: UploadFile = File(...),
    allow_overwrite: bool = Form(False),
) -> dict[str, object]:
    try:
        result = await save_upload(
            UploadRequest(
                target_dir=target_dir,
                upload=file,
                allow_overwrite=allow_overwrite,
            )
        )
    except UploadConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",
        "path": str(result.destination),
        "archive_name": result.archive_name,
        "extracted_files": result.extracted_files,
    }
