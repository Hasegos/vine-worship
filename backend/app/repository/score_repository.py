from functools import lru_cache
import json
from pathlib import Path
from app.core.paths import REFERENCE, REFERENCE_IMAGE
from app.engine.music.score import Chord, Event, KEYS, Measure, Pitch, Score


def example_score() -> Score:
    """공개 저장소용으로 직접 작성한 16마디 예제를 반환한다."""
    patterns = [
        ("G4 B4 D5 B4", "G", "오 늘 우 리"),
        ("A4 G4 E4 G4", "C/G", "함 께 걷 는"),
        ("F#4 A4 C5 A4", "D7", "길 에 기 쁨"),
        ("G4 B4 G4 R", "G", "이 가 득"),
    ]
    measures = []
    for index in range(16):
        pitches, chord, lyrics = patterns[index % 4]
        words = lyrics.split()
        events = tuple(
            Event(
                (Pitch.parse(pitch),) if pitch != "R" else (),
                4,
                (words[i],) if i < len(words) else (),
            )
            for i, pitch in enumerate(pitches.split())
        )
        measures.append(Measure(events, (Chord.parse(0, chord),), index % 4 == 0))
    return Score("함께 걷는 연습", "G", tuple(measures), "Vine Worship · 직접 작성 예제").validate()


def load_score(path: Path) -> Score:
    """로컬 채보 JSON의 크기·형식·음악 연결을 검증한다."""
    if path.stat().st_size > 2_000_000:
        raise ValueError("검증 악보 JSON은 2MB 이하여야 합니다.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("key") not in KEYS or not isinstance(data.get("title"), str):
        raise ValueError("악보 제목과 원본 키를 확인해 주세요.")
    measures = []
    if not isinstance(data.get("measures"), list) or not 1 <= len(data["measures"]) <= 128:
        raise ValueError("마디 수를 확인해 주세요.")
    for item in data["measures"]:
        if not isinstance(item.get("events"), list) or not 1 <= len(item["events"]) <= 64:
            raise ValueError("마디의 이벤트 수를 확인해 주세요.")
        events = []
        for event in item["events"]:
            if type(event.get("duration")) is not int:
                raise ValueError("음표 길이는 정수 tick이어야 합니다.")
            if any(type(event.get(key, False)) is not bool for key in ("tie_start", "tie_stop")):
                raise ValueError("붙임줄 상태를 확인해 주세요.")
            lyrics = event.get("lyrics", [])
            if not isinstance(lyrics, list) or any(not isinstance(word, str) for word in lyrics):
                raise ValueError("가사는 문자열 목록이어야 합니다.")
            events.append(
                Event(
                    tuple(Pitch.parse(value) for value in event["pitches"]),
                    event["duration"],
                    tuple(lyrics),
                    tuple(event.get("beams", [])),
                    event.get("tie_start", False),
                    event.get("tie_stop", False),
                )
            )
        measures.append(
            Measure(
                tuple(events),
                tuple(Chord.parse(mark[0], mark[1]) for mark in item.get("chords", [])),
                bool(item.get("new_system", False)),
            )
        )
    return Score(data["title"], data["key"], tuple(measures), data.get("composer", "")).validate()


@lru_cache(maxsize=1)
def source_score() -> Score:
    """로컬 비교 악보가 있으면 사용하고, 없으면 직접 작성 예제를 사용한다."""
    return load_score(REFERENCE) if REFERENCE.exists() else example_score()


def source_info() -> tuple[str, Path | None]:
    """로컬 파일 존재 여부와 이미지 접근을 Repository 안에 한정한다."""
    if REFERENCE.is_file():
        image = REFERENCE_IMAGE if REFERENCE_IMAGE.is_file() else None
        return "수동 채보 비교 악보", image
    return "직접 작성한 검증 예제", None