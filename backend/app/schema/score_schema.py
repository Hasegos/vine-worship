from pydantic import BaseModel


class ScoreResponse(BaseModel):
    """고정 원본 정보와 새로 출력할 MusicXML."""

    title: str
    original_key: str
    target_key: str
    semitones: int
    measure_count: int
    source_hash: str
    source_kind: str
    reference_image: str | None
    xml: str