from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class AssetResponse(BaseModel):
    """DB 바이트 내용을 제외한 업로드 완료 정보."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    original_name: str
    content_type: str
    byte_size: int
    chunk_count: int
    sha256: str
    status: str
    created_at: datetime