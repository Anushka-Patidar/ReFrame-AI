from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise ValueError("Invalid ObjectId.")
    return ObjectId(value)


def serialize_id(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    document["id"] = str(document.pop("_id"))
    return document
