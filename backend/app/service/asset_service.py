from collections.abc import AsyncIterable, AsyncIterator
from pathlib import PurePosixPath
from uuid import UUID

from app.core.config import settings
from app.exception.business_exception import BusinessException
from app.repository import asset_repository
from app.schema.asset_schema import AssetResponse

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
    """경로·제어 문자를 거절하고 지원하는 확장자의 MIME을 반환한다."""
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
    """확장자만 바꾼 파일을 거절한다. 전체 악보 해석은 인식 단계에서 수행한다."""
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
    """파일 크기와 무관하게 설정된 크기의 버퍼로 원본을 분할한다."""
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
    """형식 검증 후 원본을 보관한다. 분석 결과를 생성한 것으로 표시하지 않는다."""
    content_type = file_type(name)
    asset = await asset_repository.store_asset(
        name, content_type, split_chunks(stream, content_type), expected_size
    )
    return AssetResponse.model_validate(asset)


async def metadata(asset_id: UUID) -> AssetResponse:
    """다운로드 경로와 별개로 원본 보관 상태를 제공한다."""
    return AssetResponse.model_validate(await asset_repository.get_asset(asset_id))


async def download(asset_id: UUID) -> tuple[AssetResponse, AsyncIterator[bytes]]:
    """완료 원본 정보와 DB 스트림을 Controller에 전달한다."""
    asset = await asset_repository.get_asset(asset_id)
    return AssetResponse.model_validate(asset), asset_repository.read_chunks(asset)