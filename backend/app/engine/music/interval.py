from app.engine.music.score import KEYS, Pitch, STEPS


def interval(source: str, target: str) -> tuple[int, int]:
    """가장 가까운 목표 조성의 반음·음이름 이동량을 계산한다."""
    if source not in KEYS or target not in KEYS:
        raise ValueError("지원하는 장조를 선택해 주세요.")
    start, end = Pitch.parse(source + "4"), Pitch.parse(target + "4")
    semitones = (end.midi - start.midi) % 12
    if semitones > 6 or (semitones == 6 and end.midi < start.midi):
        semitones -= 12
    steps = (
        (STEPS.index(end.step) - STEPS.index(start.step)) % 7
        if semitones >= 0
        else -((STEPS.index(start.step) - STEPS.index(end.step)) % 7)
    )
    return semitones, steps