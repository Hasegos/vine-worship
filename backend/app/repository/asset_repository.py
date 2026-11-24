from collections.abc import AsyncIterable, AsyncIterator
import hashlib
from uuid import UUID
from sqlalchemy import func, insert, select

from app.db.session import session_factory
from app.exception.business_exception import BusinessException
from app.model.asset_chunk_model import AssetChunkModel
from app.model.asset_model import AssetModel


async def store_asset(
    name: str, content_type: str, chunks: AsyncIterable[bytes], expected_size: int | None
) -> AssetModel:
    """전체 파일을 적재하지 않고 저장하며 실패·중단 시 전체 업로드를 롤백한다.

    Args:
        name: 원본 파일명.
        content_type: 검증할 원본 MIME 형식.
        chunks: 형식 확인과 버퍼 분할을 마친 원본 바이트 스트림.
        expected_size: 전송 길이가 제공된 경우 비교할 실제 바이트 수.
    Returns:
        해시와 조각 수를 포함한 업로드 완료 메타데이터.
    Raises:
        BusinessException: 빈 파일이거나 선언한 전송 길이와 수신 길이가 다른 경우.
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
    """완료된 원본의 정보만 반환하며 미완료·없는 ID는 동일하게 처리한다.

    Args:
        asset_id: 완료 원본의 UUID.
    Returns:
        완료 상태의 원본 메타데이터.
    Raises:
        BusinessException: 완료된 원본이 없는 경우.
    """
    async with session_factory()() as session:
        asset = await session.scalar(
            select(AssetModel).where(AssetModel.id == asset_id, AssetModel.status == "complete")
        )
        if asset is None:
            raise BusinessException("저장된 원본을 찾을 수 없습니다.", 404, "ASSET_NOT_FOUND")
        return asset


async def list_assets(page: int, page_size: int) -> tuple[list[AssetModel], int]:
    """바이너리를 읽지 않고 완료 원본의 최신 목록을 조회한다.

    Args:
        page: 1부터 시작하는 페이지 번호.
        page_size: 한 번에 조회할 메타데이터 수.
    Returns:
        완료 원본 메타데이터 목록과 전체 개수.
    """
    async with session_factory()() as session:
        total = await session.scalar(
            select(func.count()).select_from(AssetModel).where(AssetModel.status == "complete")
        )
        result = await session.scalars(
            select(AssetModel)
            .where(AssetModel.status == "complete")
            .order_by(AssetModel.created_at.desc(), AssetModel.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result), total or 0


async def read_chunks(asset: AssetModel) -> AsyncIterator[bytes]:
    """서버 측 커서로 조각을 하나씩 읽고 누락·훼손된 스트림은 중단한다.

    Args:
        asset: 완료 원본의 메타데이터.
    Yields:
        조각 순서대로 읽은 원본 바이트.
    Raises:
        RuntimeError: 저장된 원본 조각의 순서나 무결성이 맞지 않는 경우.
    """
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