from dataclasses import dataclass
import re

STEPS = "CDEFGAB"
NATURAL = (0, 2, 4, 5, 7, 9, 11)
KEYS = {
    "C": 0,
    "Db": -5,
    "D": 2,
    "Eb": -3,
    "E": 4,
    "F": -1,
    "F#": 6,
    "G": 1,
    "Ab": -4,
    "A": 3,
    "Bb": -2,
    "B": 5,
}
QUALITY = {
    "": "major",
    "m": "minor",
    "7": "dominant",
    "m7": "minor-seventh",
    "maj7": "major-seventh",
    "sus4": "suspended-fourth",
    "add2": "major",
    "m7(b5)": "half-diminished",
    "dim": "diminished",
    "aug": "augmented",
}


@dataclass(frozen=True)
class Pitch:
    """음이름·임시표·옥타브를 보존하는 계산용 음높이."""

    step: str
    alter: int
    octave: int

    def __post_init__(self) -> None:
        """음악 데이터의 지원 범위와 일관성을 검증한다.

        Raises:
            ValueError: 지원 범위나 음악 데이터 형식이 올바르지 않은 경우.
        """
        if (
            not isinstance(self.step, str)
            or self.step not in STEPS
            or len(self.step) != 1
            or type(self.alter) is not int
            or type(self.octave) is not int
            or not -2 <= self.alter <= 2
            or not 0 <= self.octave <= 9
        ):
            raise ValueError("유효하지 않은 음높이입니다.")
        if not 0 <= self.midi <= 127:
            raise ValueError("지원 음역을 벗어났습니다.")

    @property
    def midi(self) -> int:
        """음이름·임시표·옥타브에서 실제 음높이를 계산한다.

        Returns:
            실제 음높이를 나타내는 MIDI 번호.
        """
        return 12 * (self.octave + 1) + NATURAL[STEPS.index(self.step)] + self.alter

    @property
    def name(self) -> str:
        """음이름과 임시표의 표기를 만든다.

        Returns:
            옥타브를 제외한 음이름과 임시표.
        """
        return self.step + ("#" * self.alter if self.alter >= 0 else "b" * -self.alter)

    @classmethod
    def parse(cls, value: str) -> "Pitch":
        """음높이 문자열을 음이름·임시표·옥타브로 분리한다.

        Args:
            value: 음높이 문자열.
        Returns:
            형식을 검증한 음높이.
        Raises:
            ValueError: 지원 범위나 음악 데이터 형식이 올바르지 않은 경우.
        """
        if not isinstance(value, str):
            raise ValueError("음높이는 문자열이어야 합니다.")
        match = re.fullmatch(r"([A-G])(#{1,2}|b{1,2})?([0-9])", value)
        if not match:
            raise ValueError("음높이는 C4, F#4 형식이어야 합니다.")
        accidental = match[2] or ""
        return cls(match[1], accidental.count("#") - accidental.count("b"), int(match[3]))


@dataclass(frozen=True)
class Chord:
    """근음·종류·분수 베이스와 마디 안의 시작 위치."""

    onset: int
    root: Pitch
    quality: str = ""
    bass: Pitch | None = None

    def __post_init__(self) -> None:
        """음악 데이터의 지원 범위와 일관성을 검증한다.

        Raises:
            ValueError: 지원 범위나 음악 데이터 형식이 올바르지 않은 경우.
        """
        if type(self.onset) is not int or not 0 <= self.onset < 16 or self.quality not in QUALITY:
            raise ValueError("코드의 위치와 종류를 확인해 주세요.")

    @classmethod
    def parse(cls, onset: int, label: str) -> "Chord":
        """코드 문자열을 근음·성질·분수 베이스로 분리한다.

        Args:
            onset: 마디 시작 기준 코드 위치 tick.
            label: 근음·성질·분수 베이스를 포함한 코드 문자열.
        Returns:
            형식을 검증한 코드 데이터.
        Raises:
            ValueError: 지원 범위나 음악 데이터 형식이 올바르지 않은 경우.
        """
        if not isinstance(label, str):
            raise ValueError("코드는 문자열이어야 합니다.")
        label = label.replace("♯", "#").replace("♭", "b").replace("(add2)", "add2")
        match = re.fullmatch(r"([A-G][#b]?)([^/]*)(?:/([A-G][#b]?))?", label)
        if not match or match[2] not in QUALITY or type(onset) is not int or not 0 <= onset < 16:
            raise ValueError("지원하지 않는 코드 또는 코드 위치입니다.")
        return cls(
            onset,
            Pitch.parse(match[1] + "4"),
            match[2],
            Pitch.parse(match[3] + "4") if match[3] else None,
        )

    @property
    def label(self) -> str:
        """코드의 근음·성질·분수 베이스 표기를 만든다.

        Returns:
            근음·성질·분수 베이스의 코드 표기.
        """
        return self.root.name + self.quality + ("/" + self.bass.name if self.bass else "")


@dataclass(frozen=True)
class Event:
    """동일 길이 겹음 또는 쉼표와 가사·빔·붙임줄."""

    pitches: tuple[Pitch, ...]
    duration: int
    lyrics: tuple[str, ...] = ()
    beams: tuple[str, ...] = ()
    tie_start: bool = False
    tie_stop: bool = False


@dataclass(frozen=True)
class Measure:
    """연주 순서대로 놓인 이벤트와 코드의 한 마디."""

    events: tuple[Event, ...]
    chords: tuple[Chord, ...]
    new_system: bool = False


@dataclass(frozen=True)
class Score:
    """원본과 파생본을 구분하는 불변 음악 데이터."""

    title: str
    key: str
    measures: tuple[Measure, ...]
    composer: str = ""

    def validate(self) -> "Score":
        """현재 지원 범위인 4/4·단일 리듬 성부의 길이와 연결을 검증한다.

        Returns:
            검증을 통과한 동일한 불변 악보.
        Raises:
            ValueError: 지원 범위나 음악 데이터 형식이 올바르지 않은 경우.
        """
        if (
            self.key not in KEYS
            or not 1 <= len(self.measures) <= 128
            or not 1 <= len(self.title.strip()) <= 120
        ):
            raise ValueError("악보 제목·키·마디 수를 확인해 주세요.")
        pending = None
        for measure in self.measures:
            if sum(event.duration for event in measure.events) != 16:
                raise ValueError("마디 길이는 4/4박자와 일치해야 합니다.")
            onsets, cursor = set(), 0
            for event in measure.events:
                onsets.add(cursor)
                cursor += event.duration
                if (
                    type(event.duration) is not int
                    or event.duration not in (1, 2, 3, 4, 6, 8, 12, 16)
                    or len(event.pitches) > 8
                ):
                    raise ValueError("지원하지 않는 음표 길이 또는 겹음입니다.")
                if any(
                    beam not in ("begin", "continue", "end", "forward hook", "backward hook")
                    for beam in event.beams
                ):
                    raise ValueError("빔 정보를 확인해 주세요.")
                if len(event.lyrics) > 4 or any(len(text) > 24 for text in event.lyrics):
                    raise ValueError("가사 길이를 확인해 주세요.")
                if event.tie_stop != (pending is not None) or (
                    pending is not None and pending != event.pitches
                ):
                    raise ValueError("붙임줄의 앞뒤 음높이가 일치하지 않습니다.")
                if (event.tie_start or event.tie_stop) and not event.pitches:
                    raise ValueError("쉼표에는 붙임줄을 연결할 수 없습니다.")
                pending = event.pitches if event.tie_start else None
            if any(chord.onset not in onsets for chord in measure.chords):
                raise ValueError("코드는 이벤트 시작 박에 연결되어야 합니다.")
        if pending is not None:
            raise ValueError("종료되지 않은 붙임줄이 있습니다.")
        return self