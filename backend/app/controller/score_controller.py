from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, Response
from app.exception.business_exception import BusinessException
from app.schema.score_schema import ScoreResponse
from app.service.score_service import reference_image_path, score_result

router = APIRouter()


@router.get("/api/score", response_model=ScoreResponse)
def score(key: str | None = Query(default=None, max_length=2)) -> dict:
    """고정된 검증 원본을 목표 키로 변환한다. 업로드 자동 인식과는 별도다.

    Args:
        key: 목표 키. None이면 고정 원본을 조회한다.
    Returns:
        고정 원본 정보와 변환 음악 데이터.
    Raises:
        BusinessException: 지원하지 않는 목표 키인 경우.
    """
    try:
        return score_result(key)
    except ValueError as error:
        raise BusinessException(str(error)) from error


@router.get("/score.musicxml")
def download(key: str = Query(default="D", max_length=2)) -> Response:
    """화면에 표시한 목표 키의 음악 데이터를 파일로 제공한다.

    Args:
        key: 고정 원본에서 계산할 목표 키.
    Returns:
        선택한 목표 키의 MusicXML 첨부 응답.
    """
    result = score(key)
    name = result["target_key"].replace("#", "sharp")
    return Response(
        result["xml"],
        media_type="application/vnd.recordare.musicxml+xml",
        headers={"Content-Disposition": f'attachment; filename="vine-worship-{name}.musicxml"'},
    )


@router.get("/reference-image")
def reference() -> FileResponse:
    """로컬 검증 원본만 제공하고 임의 경로 입력은 받지 않는다.

    Returns:
        검증 원본 이미지 응답.
    """
    return FileResponse(reference_image_path(), media_type="image/png")