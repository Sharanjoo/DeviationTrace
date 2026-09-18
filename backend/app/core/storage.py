import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()


def save_upload(org_id: uuid.UUID, filename: str, content: bytes) -> str:
    """Local filesystem storage. Swap point for S3 in a later milestone —
    callers only depend on this function, not on the filesystem directly."""
    org_dir = Path(settings.storage_dir) / str(org_id)
    org_dir.mkdir(parents=True, exist_ok=True)
    dest = org_dir / f"{uuid.uuid4()}_{filename}"
    dest.write_bytes(content)
    return str(dest)
