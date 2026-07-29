from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOADS_ROOT = PROJECT_ROOT / "uploads"
ROOM_UPLOADS_ROOT = UPLOADS_ROOT / "rooms"
GENERATED_UPLOADS_ROOT = UPLOADS_ROOT / "generated"
MASKS_UPLOADS_ROOT = UPLOADS_ROOT / "masks"
TEMP_UPLOADS_ROOT = UPLOADS_ROOT / "tmp"
STRUCTURE_UPLOADS_ROOT = TEMP_UPLOADS_ROOT / "structure"


def ensure_upload_directories() -> None:
    ROOM_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    GENERATED_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    MASKS_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    TEMP_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    STRUCTURE_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)


async def save_room_upload(upload: UploadFile) -> str:
    content_type = upload.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image uploads are supported.",
        )

    suffix = Path(upload.filename or "upload.jpg").suffix or ".jpg"
    filename = f"{uuid4().hex}{suffix.lower()}"
    target_path = ROOM_UPLOADS_ROOT / filename

    file_bytes = await upload.read()
    target_path.write_bytes(file_bytes)
    return filename


async def save_mask_upload(upload: UploadFile, *, room_id: str) -> str:
    """
    Save a user-painted region mask.

    Returns a relative path under `UPLOADS_ROOT` so it can be mounted via
    FastAPI static files.
    """
    content_type = upload.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image masks are supported.",
        )

    suffix = Path(upload.filename or "mask.png").suffix or ".png"
    if suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        suffix = ".png"

    filename = f"{uuid4().hex}{suffix.lower()}"
    target_dir = MASKS_UPLOADS_ROOT / room_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename

    file_bytes = await upload.read()
    target_path.write_bytes(file_bytes)
    return str(target_path.relative_to(UPLOADS_ROOT)).replace("\\", "/")
