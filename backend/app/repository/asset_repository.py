from collections.abc import AsyncIterable, AsyncIterator
import hashlib
from uuid import UUID
from sqlalchemy import insert, select

from app.db.session import session_factory
from app.exception.business_exception import BusinessException
from app.model.asset_chunk_model import AssetChunkModel
from app.model.asset_model import AssetModel


async def store_asset(
    name: str, content_type: str, chunks: AsyncIterable[bytes], expected_size: int | None
) -> AssetModel:
    """전체 파일을 적재하지 않고 저장하며 실패·중단 시 전체 업로드를 롤백한다.

    Args:
        chunks: Service에서 형식 확인과 버퍼 분할을 마친 원본 바이트.
        expected_size: 전송 길이가 제공된 경우 확인할 실제 파일 바이트 수.
    Returns:
        원본 해시와 조각 수를 포함한 완료 메타데이터.
    """
    async with session_factory()() as session, session.begin():
        asset = AssetModel(
            original_name=name,
            content_type=content_type,
            byte_size=0,
            chunk_count=0,
            status="receiving",
        )
        session.add(asset)
        await session.flush()
        digest = hashlib.sha256()
        async for chunk in chunks:
            await session.execute(
                insert(AssetChunkModel).values(
                    asset_id=asset.id, sequence=asset.chunk_count, content=chunk
                )
            )
            asset.byte_size += len(chunk)
            asset.chunk_count += 1
            digest.update(chunk)
        if asset.byte_size == 0 or (expected_size is not None and asset.byte_size != expected_size):
            raise BusinessException("파일이 비어 있거나 전송이 완료되지 않았습니다.")
        asset.sha256 = digest.hexdigest()
        asset.status = "complete"
        await session.flush()
    return asset


async def get_asset(asset_id: UUID) -> AssetModel:
    """완료된 원본의 정보만 반환하며 미완료·없는 ID는 동일하게 처리한다."""
    async with session_factory()() as session:
        asset = await session.scalar(
            select(AssetModel).where(AssetModel.id == asset_id, AssetModel.status == "complete")
        )
        if asset is None:
            raise BusinessException("저장된 원본을 찾을 수 없습니다.", 404, "ASSET_NOT_FOUND")
        return asset


async def read_chunks(asset: AssetModel) -> AsyncIterator[bytes]:
    """서버 측 커서로 조각을 하나씩 읽고 누락·훼손된 스트림은 중단한다."""
    size, count, digest = 0, 0, hashlib.sha256()
    async with session_factory()() as session:
        result = await session.stream(
            select(AssetChunkModel.sequence, AssetChunkModel.content)
            .where(AssetChunkModel.asset_id == asset.id)
            .order_by(AssetChunkModel.sequence)
            .execution_options(yield_per=1)
        )
        try:
            async for sequence, content in result:
                if sequence != count:
                    raise RuntimeError("Stored asset chunk sequence mismatch")
                count += 1
                size += len(content)
                digest.update(content)
                yield content
            if (
                count != asset.chunk_count
                or size != asset.byte_size
                or digest.hexdigest() != asset.sha256
            ):
                raise RuntimeError("Stored asset checksum mismatch")
        finally:
            await result.close()