from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AssetResponse(BaseModel):
    """DB 바이트 내용을 제외한 업로드 완료 정보."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    original_name: str
    content_type: str
    byte_size: int
    chunk_count: int
    sha256: str
    status: str
    created_at: datetime


class AssetListResponse(BaseModel):
    """완료 원본 목록의 페이지 정보."""

    items: list[AssetResponse]
    total: int
    page: int
    page_size: int