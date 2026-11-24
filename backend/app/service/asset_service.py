from collections.abc import AsyncIterable, AsyncIterator
from pathlib import PurePosixPath
from uuid import UUID

from app.core.config import settings
from app.exception.business_exception import BusinessException
from app.repository import asset_repository
from app.schema.asset_schema import AssetListResponse, AssetResponse

CHUNK_SIZE = settings.UPLOAD_CHUNK_SIZE
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
}


def file_type(name: str) -> str:
    """경로·제어 문자를 거절하고 지원하는 확장자의 MIME을 반환한다.

    Args:
        name: 원본 파일명.
    Returns:
        지원 확장자에 대응하는 MIME 형식.
    Raises:
        BusinessException: 파일명에 경로·제어 문자가 있거나 지원하지 않는 확장자인 경우.
    """
    if (
        not name
        or len(name) > 255
        or any(ord(c) < 32 or ord(c) == 127 for c in name)
        or "/" in name
        or "\\" in name
    ):
        raise BusinessException("경로가 없는 255자 이하의 파일명을 사용해 주세요.")
    content_type = CONTENT_TYPES.get(PurePosixPath(name).suffix.lower())
    if content_type is None:
        raise BusinessException(
            "PDF·PNG·JPEG·MP4·WebM 파일을 선택해 주세요.", 415, "UNSUPPORTED_FILE"
        )
    return content_type


def validate_signature(prefix: bytes, content_type: str) -> None:
    """확장자만 바꾼 파일을 거절한다. 전체 악보 해석은 인식 단계에서 수행한다.

    Args:
        prefix: 원본 첫 부분의 시그니처 바이트.
        content_type: 검증할 원본 MIME 형식.
    Raises:
        BusinessException: 파일 시그니처가 확장자와 일치하지 않는 경우.
    """
    valid = {
        "application/pdf": prefix.startswith(b"%PDF-"),
        "image/png": prefix.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/jpeg": prefix.startswith(b"\xff\xd8\xff"),
        "video/mp4": len(prefix) >= 12 and prefix[4:8] == b"ftyp",
        "video/webm": prefix.startswith(b"\x1aE\xdf\xa3"),
    }
    if not valid.get(content_type):
        raise BusinessException("파일 내용이 확장자와 일치하지 않습니다.", 415, "INVALID_FILE")


async def split_chunks(stream: AsyncIterable[bytes], content_type: str) -> AsyncIterator[bytes]:
    """파일 크기와 무관하게 설정된 크기의 버퍼로 원본을 분할한다.

    Args:
        stream: 아직 전체 적재하지 않은 원본 바이트 스트림.
        content_type: 검증할 원본 MIME 형식.
    Yields:
        설정된 버퍼 크기 이하의 원본 바이트 조각.
    """
    buffer = bytearray()
    checked = False
    async for block in stream:
        view = memoryview(block)
        offset = 0
        while offset < len(view):
            size = min(CHUNK_SIZE - len(buffer), len(view) - offset)
            buffer.extend(view[offset : offset + size])
            offset += size
            if len(buffer) == CHUNK_SIZE:
                if not checked:
                    validate_signature(bytes(buffer[:32]), content_type)
                    checked = True
                yield bytes(buffer)
                buffer.clear()
    if buffer:
        if not checked:
            validate_signature(bytes(buffer[:32]), content_type)
        yield bytes(buffer)


async def upload(
    name: str, stream: AsyncIterable[bytes], expected_size: int | None
) -> AssetResponse:
    """형식 검증 후 원본을 보관한다. 분석 결과를 생성한 것으로 표시하지 않는다.

    Args:
        name: 원본 파일명.
        stream: 아직 전체 적재하지 않은 원본 바이트 스트림.
        expected_size: 전송 길이가 제공된 경우 비교할 실제 바이트 수.
    Returns:
        원본 저장 완료 메타데이터.
    """
    content_type = file_type(name)
    asset = await asset_repository.store_asset(
        name, content_type, split_chunks(stream, content_type), expected_size
    )
    return AssetResponse.model_validate(asset)


async def metadata(asset_id: UUID) -> AssetResponse:
    """다운로드 경로와 별개로 원본 보관 상태를 제공한다.

    Args:
        asset_id: 완료 원본의 UUID.
    Returns:
        파일 내용과 비밀값을 제외한 원본 정보.
    """
    return AssetResponse.model_validate(await asset_repository.get_asset(asset_id))


async def list_assets(page: int) -> AssetListResponse:
    """DB 원본을 바이너리와 분리해 페이지 단위로 제공한다.

    Args:
        page: 1부터 시작하는 페이지 번호.
    Returns:
        원본 목록과 전체 개수 및 페이지 정보.
    """
    page_size = 12
    assets, total = await asset_repository.list_assets(page, page_size)
    return AssetListResponse(
        items=[AssetResponse.model_validate(asset) for asset in assets],
        total=total,
        page=page,
        page_size=page_size,
    )


async def preview(asset_id: UUID) -> tuple[AssetResponse, AsyncIterator[bytes]]:
    """브라우저 표시가 가능한 원본만 DB 스트림으로 제공한다.

    Args:
        asset_id: 완료 원본의 UUID.
    Returns:
        이미지 또는 PDF 정보와 원본 바이트 스트림.
    Raises:
        BusinessException: 미리보기를 지원하지 않는 형식인 경우.
    """
    asset, chunks = await download(asset_id)
    if asset.content_type not in {"image/png", "image/jpeg", "application/pdf"}:
        raise BusinessException("이미지와 PDF만 미리볼 수 있습니다.", 415, "PREVIEW_UNSUPPORTED")
    return asset, chunks


async def download(asset_id: UUID) -> tuple[AssetResponse, AsyncIterator[bytes]]:
    """완료 원본 정보와 DB 스트림을 Controller에 전달한다.

    Args:
        asset_id: 완료 원본의 UUID.
    Returns:
        완료 메타데이터와 순서대로 읽을 DB 스트림.
    """
    asset = await asset_repository.get_asset(asset_id)
    return AssetResponse.model_validate(asset), asset_repository.read_chunks(asset)