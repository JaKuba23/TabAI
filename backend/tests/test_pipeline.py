import numpy as np
import pytest


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

TUNINGS = {
    "standard": [64, 59, 55, 50, 45, 40],
    "drop_d": [64, 59, 55, 50, 45, 38],
    "open_g": [62, 59, 55, 50, 43, 38],
    "half_down": [63, 58, 54, 49, 44, 39],
    "open_e": [64, 59, 56, 52, 47, 40],
}

OPEN_CHORD_DIFFICULTY: dict[str, int] = {
    "C": 1, "Am": 1, "G": 1, "Em": 1, "D": 1, "A": 1, "E": 1, "Dm": 2,
    "G7": 2, "A7": 2, "E7": 2, "D7": 2, "Bm": 4, "F": 3, "B": 5,
    "Bb": 5, "F#m": 4,
}

CHORD_QUALITIES = ["", "m", "7", "m7", "maj7", "dim", "sus2", "sus4"]


def _transpose_chord(chord_name: str, semitones: int) -> str:
    if not chord_name:
        return chord_name
    if len(chord_name) > 1 and chord_name[1] in ("#", "b"):
        root = chord_name[:2]
        quality = chord_name[2:]
    else:
        root = chord_name[0]
        quality = chord_name[1:]

    flat_map = {"Db": "C#", "Eb": "D#", "Fb": "E", "Gb": "F#", "Ab": "G#", "Bb": "A#", "Cb": "B"}
    root = flat_map.get(root, root)

    if root not in NOTE_NAMES:
        return chord_name

    idx = NOTE_NAMES.index(root)
    new_idx = (idx + semitones) % 12
    return NOTE_NAMES[new_idx] + quality


def _suggest_capo(chords: list[dict]) -> int:
    if not chords:
        return 0
    best_capo = 0
    best_score = float("inf")
    for capo in range(8):
        score = capo * 0.5
        for c in chords:
            transposed = _transpose_chord(c["chord"], -capo)
            score += OPEN_CHORD_DIFFICULTY.get(transposed, 6)
        if score < best_score:
            best_score = score
            best_capo = capo
    return best_capo


def _build_chord_templates() -> dict[str, np.ndarray]:
    intervals = {
        "": [0, 4, 7],
        "m": [0, 3, 7],
        "7": [0, 4, 7, 10],
        "m7": [0, 3, 7, 10],
        "maj7": [0, 4, 7, 11],
        "dim": [0, 3, 6],
        "sus2": [0, 2, 7],
        "sus4": [0, 5, 7],
    }
    templates: dict[str, np.ndarray] = {}
    for root_idx, root_name in enumerate(NOTE_NAMES):
        for quality, ints in intervals.items():
            chroma = np.zeros(12)
            for interval in ints:
                chroma[(root_idx + interval) % 12] = 1.0
            chroma /= chroma.sum()
            templates[f"{root_name}{quality}"] = chroma
    return templates


def _assign_tab_note(
    pitch: int, tuning: list[int], prev_position: float
) -> tuple[int, int, float]:
    best_string = 0
    best_fret = 0
    best_cost = float("inf")
    for string_idx, open_note in enumerate(tuning):
        fret = pitch - open_note
        if not (0 <= fret <= 22):
            continue
        cost = (
            fret * 0.1
            + string_idx * 0.05
            + max(0, fret - 4) * 2.0
            + abs(fret - prev_position) * 0.15
        )
        if cost < best_cost:
            best_cost = cost
            best_string = string_idx
            best_fret = fret
    new_prev = prev_position * 0.7 + best_fret * 0.3
    return best_string, best_fret, new_prev


# --- Tests ---


class TestSmartCapo:
    def test_g_c_d_suggests_capo_0(self):
        chords = [{"chord": "G"}, {"chord": "C"}, {"chord": "D"}]
        assert _suggest_capo(chords) == 0

    def test_f_bb_suggests_capo_gt_0(self):
        chords = [{"chord": "F"}, {"chord": "Bb"}, {"chord": "F"}, {"chord": "Bb"}]
        capo = _suggest_capo(chords)
        assert capo > 0

    def test_empty_chords_returns_0(self):
        assert _suggest_capo([]) == 0

    def test_capo_range(self):
        chords = [{"chord": "Ab"}, {"chord": "Db"}, {"chord": "Eb"}]
        capo = _suggest_capo(chords)
        assert 0 <= capo <= 7


class TestChordTranspose:
    def test_g_plus_2_is_a(self):
        assert _transpose_chord("G", 2) == "A"

    def test_am_minus_2_is_gm(self):
        assert _transpose_chord("Am", -2) == "Gm"

    def test_c_plus_12_is_c(self):
        assert _transpose_chord("C", 12) == "C"

    def test_sharp_chord(self):
        assert _transpose_chord("F#m", 1) == "Gm"

    def test_flat_chord(self):
        assert _transpose_chord("Bb", 2) == "C"

    def test_empty_chord(self):
        assert _transpose_chord("", 5) == ""


class TestChordTemplates:
    def test_all_roots_and_qualities_exist(self):
        templates = _build_chord_templates()
        for root in NOTE_NAMES:
            for quality in CHORD_QUALITIES:
                name = f"{root}{quality}"
                assert name in templates, f"Missing template: {name}"

    def test_templates_sum_to_1(self):
        templates = _build_chord_templates()
        for name, t in templates.items():
            assert abs(t.sum() - 1.0) < 1e-6, f"Template {name} does not sum to 1"

    def test_total_count(self):
        templates = _build_chord_templates()
        assert len(templates) == 12 * len(CHORD_QUALITIES)


class TestTabGeneration:
    def test_fret_range(self):
        for tuning_name, tuning in TUNINGS.items():
            for pitch in range(40, 90):
                prev = 3.0
                string_idx, fret, _ = _assign_tab_note(pitch, tuning, prev)
                playable = any(0 <= pitch - o <= 22 for o in tuning)
                if playable:
                    assert 0 <= fret <= 22, (
                        f"Fret {fret} out of range for pitch {pitch} "
                        f"in tuning {tuning_name}"
                    )

    def test_no_impossible_stretch(self):
        tuning = TUNINGS["standard"]
        prev = 3.0
        notes = [60, 64, 67, 72, 76]
        frets: list[int] = []
        for pitch in notes:
            _, fret, prev = _assign_tab_note(pitch, tuning, prev)
            frets.append(fret)
        for i in range(1, len(frets)):
            assert abs(frets[i] - frets[i - 1]) <= 10, (
                f"Impossible stretch between frets {frets[i-1]} and {frets[i]}"
            )

    def test_prev_position_smoothing(self):
        tuning = TUNINGS["standard"]
        prev = 0.0
        _, fret, new_prev = _assign_tab_note(60, tuning, prev)
        assert new_prev == prev * 0.7 + fret * 0.3


class TestTunings:
    def test_all_tunings_have_6_strings(self):
        for name, notes in TUNINGS.items():
            assert len(notes) == 6, f"Tuning {name} has {len(notes)} strings"

    def test_all_midi_values_in_range(self):
        for name, notes in TUNINGS.items():
            for note in notes:
                assert 30 <= note <= 75, (
                    f"Tuning {name} has MIDI {note} outside 30-75"
                )

    def test_strings_descending(self):
        for name, notes in TUNINGS.items():
            for i in range(len(notes) - 1):
                assert notes[i] >= notes[i + 1], (
                    f"Tuning {name} strings not descending at index {i}"
                )
