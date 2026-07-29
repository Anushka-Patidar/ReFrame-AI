from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOADS_ROOT = PROJECT_ROOT / "uploads"
ROOM_UPLOADS_ROOT = UPLOADS_ROOT / "rooms"
GENERATED_UPLOADS_ROOT = UPLOADS_ROOT / "generated"


def ensure_upload_directories() -> None:
    ROOM_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    GENERATED_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)


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
