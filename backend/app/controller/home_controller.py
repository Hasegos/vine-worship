from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.core.paths import FRONTEND

router = APIRouter()
templates = Jinja2Templates(directory=FRONTEND / "template")


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    """업로드와 음악 변환 예제를 구분한 홈 화면을 제공한다.

    Args:
        request: 현재 HTTP 요청.
    Returns:
        업로드와 음악 예제를 구분한 홈 화면.
    """
    from app.engine.music.score import KEYS

    return templates.TemplateResponse(
        request=request, name="home.html", context={"keys": tuple(KEYS)}
    )