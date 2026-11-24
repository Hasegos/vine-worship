from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from app.engine.export.musicxml import export_musicxml
from app.engine.music.interval import interval
from app.engine.music.transpose import transpose
from app.repository.score_repository import source_score, source_info
from app.exception.business_exception import BusinessException


def score_result(target: str | None) -> dict:
    """각 요청을 같은 원본에서 계산하고 원본 식별 정보와 XML을 반환한다."""
    source = source_score()
    kind, image = source_info()
    target = source.key if target is None else target
    result = transpose(source, target)
    encoded = json.dumps(asdict(source), ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {
        "title": source.title,
        "original_key": source.key,
        "target_key": target,
        "semitones": interval(source.key, target)[0],
        "measure_count": len(source.measures),
        "source_hash": hashlib.sha256(encoded).hexdigest(),
        "source_kind": kind,
        "reference_image": "/reference-image" if image else None,
        "xml": export_musicxml(result),
    }


def reference_image_path() -> Path:
    """Repository가 확인한 비교 이미지 또는 명시적인 미존재 오류를 제공한다."""
    _, image = source_info()
    if image is None:
        raise BusinessException("비교 이미지가 없습니다.", 404, "REFERENCE_NOT_FOUND")
    return image