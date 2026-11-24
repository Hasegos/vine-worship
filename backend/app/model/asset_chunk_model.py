from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AssetChunkModel(Base):
    """원본 ID·순번 복합키로 조각 순서와 중복을 관리한다."""

    __tablename__ = "asset_chunk"
    __table_args__ = (CheckConstraint("sequence >= 0"),)

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), primary_key=True
    )
    sequence: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)