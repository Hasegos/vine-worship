from dataclasses import replace
from app.engine.music.interval import interval
from app.engine.music.score import Chord, NATURAL, Pitch, STEPS, Score


def transpose_pitch(pitch: Pitch, semitones: int, steps: int) -> Pitch:
    """음정의 철자와 실제 음높이를 보존한다.

    Args:
        pitch: 음이름·임시표·옥타브를 가진 원본 음높이.
        semitones: 실제 음높이를 이동할 반음 수.
        steps: 온음계 음이름 이동 단계 수.
    Returns:
        음정 철자와 실제 높이를 보존한 새 음높이.
    """
    octave, index = divmod(pitch.octave * 7 + STEPS.index(pitch.step) + steps, 7)
    alter = pitch.midi + semitones - (12 * (octave + 1) + NATURAL[index])
    return Pitch(STEPS[index], alter, octave)


def transpose(score: Score, target: str) -> Score:
    """입력 원본을 수정하지 않고 목표 조성의 새 악보를 반환한다.

    Args:
        score: 고정 원본 음악 데이터.
        target: 목표 장조.
    Returns:
        원본을 수정하지 않은 목표 조성 악보.
    """
    semitones, steps = interval(score.key, target)
    shift = lambda pitch: transpose_pitch(pitch, semitones, steps)
    measures = tuple(
        replace(
            measure,
            events=tuple(
                replace(event, pitches=tuple(shift(pitch) for pitch in event.pitches))
                for event in measure.events
            ),
            chords=tuple(
                Chord(
                    chord.onset,
                    replace(shift(chord.root), octave=4),
                    chord.quality,
                    replace(shift(chord.bass), octave=4) if chord.bass else None,
                )
                for chord in measure.chords
            ),
        )
        for measure in score.measures
    )
    return replace(score, key=target, measures=measures).validate()