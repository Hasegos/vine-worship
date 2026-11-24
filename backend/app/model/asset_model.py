from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AssetModel(Base):
    """완료 파일만 조회하고 실제 내용은 조각 테이블에 보관한다."""

    __tablename__ = "asset"
    __table_args__ = (CheckConstraint("byte_size >= 0 AND chunk_count >= 0"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    original_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    byte_size: Mapped[int] = mapped_column(BigInteger, default=0)
    chunk_count: Mapped[int] = mapped_column(BigInteger, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="receiving")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())