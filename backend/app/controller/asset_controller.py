import asyncio
from urllib.parse import quote
from uuid import UUID
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from starlette.requests import ClientDisconnect

from app.core.config import settings
from app.exception.business_exception import BusinessException
from app.schema.asset_schema import AssetResponse
from app.service import asset_service

router = APIRouter(prefix="/api/asset")
upload_slots = asyncio.Semaphore(settings.UPLOAD_CONCURRENCY)


@router.post("", response_model=AssetResponse, status_code=201)
async def upload(
    request: Request, filename: str = Query(min_length=1, max_length=255)
) -> AssetResponse:
    """raw 파일 본문을 받아 multipart 전체 적재와 임의 용량 상한을 피한다.

    Args:
        request: 현재 HTTP 요청.
        filename: 경로를 포함하지 않은 원본 파일명.
    Returns:
        원본 저장 완료 메타데이터.
    Raises:
        BusinessException: 업로드 헤더·전송 길이가 잘못됐거나 연결이 중단된 경우.
    """
    if request.headers.get("X-Vine-Upload") != "1":
        raise BusinessException(
            "웹 업로드 화면에서 파일을 전송해 주세요.", 403, "UPLOAD_HEADER_REQUIRED"
        )
    asset_service.file_type(filename)
    length = request.headers.get("Content-Length")
    if length is not None and (not length.isdecimal() or len(length) > 19):
        raise BusinessException("전송 길이가 올바르지 않습니다.")
    async with upload_slots:
        try:
            return await asset_service.upload(
                filename, request.stream(), int(length) if length else None
            )
        except ClientDisconnect:
            raise BusinessException(
                "파일 전송 연결이 끊겼습니다.", 499, "UPLOAD_INTERRUPTED"
            ) from None


@router.get("/{asset_id}", response_model=AssetResponse)
async def metadata(asset_id: UUID) -> AssetResponse:
    """완료 원본의 파일 정보와 해시를 반환한다.

    Args:
        asset_id: 완료 원본의 UUID.
    Returns:
        파일 내용과 비밀값을 제외한 원본 정보.
    """
    return await asset_service.metadata(asset_id)


@router.get("/{asset_id}/download")
async def download(asset_id: UUID) -> StreamingResponse:
    """한글 파일명을 보존하며 DB의 원본을 순서대로 전달한다.

    Args:
        asset_id: 완료 원본의 UUID.
    Returns:
        완료 원본의 첨부 다운로드 응답.
    """
    asset, chunks = await asset_service.download(asset_id)
    encoded_name = quote(asset.original_name, safe="")
    return StreamingResponse(
        chunks,
        media_type=asset.content_type,
        headers={
            "Content-Length": str(asset.byte_size),
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
            "X-Content-SHA256": asset.sha256,
        },
    )