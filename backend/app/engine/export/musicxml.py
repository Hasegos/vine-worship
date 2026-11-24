from xml.etree.ElementTree import Element, SubElement, tostring
from app.engine.music.score import KEYS, QUALITY, Score

TYPES = {
    1: "16th",
    2: "eighth",
    3: "eighth",
    4: "quarter",
    6: "quarter",
    8: "half",
    12: "half",
    16: "whole",
}


def tag(parent: Element, name: str, value: object = None, **attrs: str) -> Element:
    """표준 XML 이스케이프를 유지하며 음악 요소를 만든다."""
    node = SubElement(parent, name, attrs)
    if value is not None:
        node.text = str(value)
    return node


def export_musicxml(score: Score) -> str:
    """음표·겹음·붙임줄·코드·복수 절 가사를 한 악보로 직렬화한다."""
    score.validate()
    root = Element("score-partwise", version="4.0")
    tag(tag(root, "work"), "work-title", score.title)
    if score.composer:
        tag(tag(root, "identification"), "creator", score.composer, type="composer")
    defaults = tag(root, "defaults")
    scaling = tag(defaults, "scaling")
    tag(scaling, "millimeters", 7)
    tag(scaling, "tenths", 40)
    part_list = tag(root, "part-list")
    tag(tag(part_list, "score-part", id="P1"), "part-name", "")
    part = tag(root, "part", id="P1")
    for index, model in enumerate(score.measures, 1):
        measure = tag(part, "measure", number=str(index))
        if model.new_system and index > 1:
            tag(measure, "print", **{"new-system": "yes"})
        if index == 1:
            attributes = tag(measure, "attributes")
            tag(attributes, "divisions", 4)
            key = tag(attributes, "key")
            tag(key, "fifths", KEYS[score.key])
            tag(key, "mode", "major")
            time = tag(attributes, "time")
            tag(time, "beats", 4)
            tag(time, "beat-type", 4)
            clef = tag(attributes, "clef")
            tag(clef, "sign", "G")
            tag(clef, "line", 2)
        onset = 0
        for event in model.events:
            for chord in (chord for chord in model.chords if chord.onset == onset):
                harmony = tag(measure, "harmony")
                chord_root = tag(harmony, "root")
                tag(chord_root, "root-step", chord.root.step)
                if chord.root.alter:
                    tag(chord_root, "root-alter", chord.root.alter)
                tag(harmony, "kind", QUALITY[chord.quality], text=chord.quality)
                if chord.bass:
                    bass = tag(harmony, "bass")
                    tag(bass, "bass-step", chord.bass.step)
                    if chord.bass.alter:
                        tag(bass, "bass-alter", chord.bass.alter)
                if chord.quality == "add2":
                    degree = tag(harmony, "degree")
                    tag(degree, "degree-value", 2)
                    tag(degree, "degree-alter", 0)
                    tag(degree, "degree-type", "add")
            for voice_index, pitch in enumerate(event.pitches or (None,)):
                note = tag(measure, "note")
                if voice_index:
                    tag(note, "chord")
                if pitch:
                    xml_pitch = tag(note, "pitch")
                    tag(xml_pitch, "step", pitch.step)
                    if pitch.alter:
                        tag(xml_pitch, "alter", pitch.alter)
                    tag(xml_pitch, "octave", pitch.octave)
                else:
                    tag(note, "rest")
                tag(note, "duration", event.duration)
                for active, kind in ((event.tie_stop, "stop"), (event.tie_start, "start")):
                    if active:
                        tag(note, "tie", type=kind)
                tag(note, "voice", 1)
                tag(note, "type", TYPES[event.duration])
                if event.duration in (3, 6, 12):
                    tag(note, "dot")
                if pitch and event.duration < 16:
                    tag(note, "stem", "down" if len(event.pitches) > 1 else "up")
                if not voice_index:
                    for level, beam in enumerate(event.beams, 1):
                        tag(note, "beam", beam, number=str(level))
                if event.tie_start or event.tie_stop:
                    notation = tag(note, "notations")
                    for active, kind in ((event.tie_stop, "stop"), (event.tie_start, "start")):
                        if active:
                            tag(notation, "tied", type=kind)
                if not voice_index:
                    for verse, syllable in enumerate(event.lyrics, 1):
                        if syllable:
                            lyric = tag(note, "lyric", number=str(verse))
                            tag(lyric, "syllabic", "single")
                            tag(lyric, "text", syllable)
            onset += event.duration
        if index == len(score.measures):
            tag(tag(measure, "barline", location="right"), "bar-style", "light-heavy")
    return tostring(root, encoding="unicode", xml_declaration=False)