"""Modal GPU worker for the full transcription pipeline.

Separates guitar stem via HTDemucs, transcribes with Basic Pitch,
detects BPM/key/chords, generates guitar tab, and exports GP5 + MIDI.
"""

from __future__ import annotations

import io
import os
import uuid
from pathlib import Path
from typing import Any

import modal

# ---------------------------------------------------------------------------
# Modal app & image
# ---------------------------------------------------------------------------

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "demucs==4.0.1",
        "torch==2.4.1",
        "torchaudio==2.4.1",
        "basic-pitch==0.3.3",
        "librosa==0.10.2",
        "soundfile==0.12.1",
        "numpy==1.26.4",
        "scipy==1.14.1",
        "music21==9.3.0",
        "mido==1.3.2",
        "pyguitarpro==0.10.1",
        "sqlalchemy[asyncio]==2.0.35",
        "asyncpg==0.29.0",
        "boto3==1.35.0",
        "pydantic-settings==2.5.2",
    )
    .apt_install("ffmpeg", "libsndfile1")
)

app = modal.App("tabai-transcription", image=image)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TUNINGS: dict[str, list[int]] = {
    "standard": [64, 59, 55, 50, 45, 40],
    "drop_d": [64, 59, 55, 50, 45, 38],
    "open_g": [62, 59, 55, 50, 43, 38],
    "half_down": [63, 58, 54, 49, 44, 39],
    "open_e": [64, 59, 56, 52, 47, 40],
}

NOTE_NAMES: list[str] = [
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B",
]

# Krumhansl-Schmuckler key profiles
MAJOR_PROFILE: list[float] = [
    6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
    2.52, 5.19, 2.39, 3.66, 2.29, 2.88,
]
MINOR_PROFILE: list[float] = [
    6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
    2.54, 4.75, 3.98, 2.69, 3.34, 3.17,
]

# Chord template: 12-element binary chroma vector for each quality
_CHORD_TEMPLATES: dict[str, list[int]] = {
    "":     [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],  # major
    "m":    [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
    "7":    [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
    "m7":   [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0],
    "maj7": [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
    "dim":  [1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0],
    "sus2": [1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    "sus4": [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0],
}

OPEN_CHORD_DIFFICULTY: dict[str, int] = {
    "C": 1, "Am": 1, "G": 1, "Em": 1, "D": 1, "A": 1, "E": 1,
    "Dm": 2, "G7": 2, "A7": 2, "E7": 2, "D7": 2,
    "Bm": 4, "F": 3, "B": 5, "Bb": 5, "F#m": 4,
}


# ---------------------------------------------------------------------------
# DB helpers  (fresh engine per call -- no shared pool in worker)
# ---------------------------------------------------------------------------

def _asyncpg_ssl_connect_args() -> dict:
    import ssl

    url = os.environ.get("DATABASE_URL", "").lower()
    if "supabase" not in url:
        return {}
    if os.environ.get("DATABASE_SSL_INSECURE", "").lower() in ("1", "true", "yes"):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return {"ssl": ctx}
    return {"ssl": True}


async def _make_engine():
    from sqlalchemy.ext.asyncio import create_async_engine

    return create_async_engine(
        os.environ["DATABASE_URL"],
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
        connect_args=_asyncpg_ssl_connect_args(),
    )


async def _update_job_status(
    job_id: str,
    status: str,
    step_message: str,
    progress_pct: int,
) -> None:
    from sqlalchemy import text

    engine = await _make_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE jobs SET status = :status, step_message = :step, "
                "progress_pct = :pct, updated_at = NOW() WHERE id = :jid"
            ),
            {"status": status, "step": step_message, "pct": progress_pct, "jid": job_id},
        )
    await engine.dispose()


async def _get_job_audio_key(job_id: str) -> str:
    from sqlalchemy import text

    engine = await _make_engine()
    async with engine.begin() as conn:
        row = await conn.execute(
            text("SELECT audio_r2_key FROM jobs WHERE id = :jid"),
            {"jid": job_id},
        )
        result = row.fetchone()
    await engine.dispose()
    if result is None or result[0] is None:
        raise ValueError(f"No audio_r2_key found for job {job_id}")
    return result[0]


async def _save_transcription(
    job_id: str,
    *,
    bpm: float,
    detected_key: str,
    tuning: str,
    capo: int,
    tab_data: dict[str, Any],
    chords: list[dict[str, Any]],
    gp5_r2_key: str,
    midi_r2_key: str,
) -> None:
    from sqlalchemy import text

    engine = await _make_engine()
    import json

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO transcriptions "
                "(id, job_id, bpm, key, time_signature, tuning, capo_suggestion, "
                "gp5_r2_key, midi_r2_key, tab_data, chords, created_at) "
                "VALUES (:tid, :jid, :bpm, :key, :ts, :tuning, :capo, "
                ":gp5, :midi, :tab::jsonb, :chords::jsonb, NOW())"
            ),
            {
                "tid": str(uuid.uuid4()),
                "jid": job_id,
                "bpm": bpm,
                "key": detected_key,
                "ts": "4/4",
                "tuning": tuning,
                "capo": capo,
                "gp5": gp5_r2_key,
                "midi": midi_r2_key,
                "tab": json.dumps(tab_data),
                "chords": json.dumps(chords),
            },
        )
    await engine.dispose()


async def _set_job_result(job_id: str, result: dict[str, Any]) -> None:
    from sqlalchemy import text
    import json

    engine = await _make_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE jobs SET result = :res::jsonb, updated_at = NOW() "
                "WHERE id = :jid"
            ),
            {"res": json.dumps(result), "jid": job_id},
        )
    await engine.dispose()


# ---------------------------------------------------------------------------
# R2 / S3 helpers
# ---------------------------------------------------------------------------

def _r2_client():
    import boto3
    from botocore.config import Config

    account_id = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def _download_from_r2(key: str) -> bytes:
    s3 = _r2_client()
    bucket = os.environ.get("R2_BUCKET_NAME", "tabai-audio")
    resp = s3.get_object(Bucket=bucket, Key=key)
    return resp["Body"].read()


def _upload_to_r2(data: bytes, key: str) -> str:
    s3 = _r2_client()
    bucket = os.environ.get("R2_BUCKET_NAME", "tabai-audio")
    s3.put_object(Bucket=bucket, Key=key, Body=data)
    return key


# ---------------------------------------------------------------------------
# Step B  -- HTDemucs source separation
# ---------------------------------------------------------------------------

def _separate_guitar(audio_path: str, guitar_path: str) -> None:
    import torch
    import torchaudio
    from demucs.apply import apply_model
    from demucs.pretrained import get_model

    model = get_model("htdemucs_6s")
    model.eval()
    if torch.cuda.is_available():
        model.cuda()

    waveform, sr = torchaudio.load(audio_path)
    if sr != model.samplerate:
        waveform = torchaudio.transforms.Resample(sr, model.samplerate)(waveform)
    if waveform.shape[0] == 1:
        waveform = waveform.repeat(2, 1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    with torch.no_grad():
        sources = apply_model(model, waveform.unsqueeze(0), device=device)

    guitar_idx = model.sources.index("guitar")
    guitar_stem = sources[0, guitar_idx]
    torchaudio.save(guitar_path, guitar_stem.cpu(), model.samplerate)


# ---------------------------------------------------------------------------
# Step C  -- Basic Pitch transcription
# ---------------------------------------------------------------------------

def _transcribe_audio(guitar_path: str) -> tuple:
    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import predict

    model_output, midi_data, note_events = predict(
        guitar_path,
        ICASSP_2022_MODEL_PATH,
        onset_threshold=0.5,
        frame_threshold=0.3,
        minimum_note_length=58,
        minimum_frequency=80,
        maximum_frequency=1400,
        melodia_trick=True,
    )
    return model_output, midi_data, note_events


# ---------------------------------------------------------------------------
# Step D  -- BPM, Key, Chords
# ---------------------------------------------------------------------------

def _detect_bpm(audio_path: str) -> float:
    import librosa
    import numpy as np

    y, sr = librosa.load(audio_path, sr=None)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo[0])
    return float(tempo)


def _detect_key(audio_path: str) -> str:
    import librosa
    import numpy as np

    y, sr = librosa.load(audio_path, sr=None)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)

    best_corr = -2.0
    best_key = "C major"

    major_profile = np.array(MAJOR_PROFILE)
    minor_profile = np.array(MINOR_PROFILE)

    for shift in range(12):
        rotated = np.roll(chroma_mean, -shift)

        corr_major = float(np.corrcoef(rotated, major_profile)[0, 1])
        if corr_major > best_corr:
            best_corr = corr_major
            best_key = f"{NOTE_NAMES[shift]} major"

        corr_minor = float(np.corrcoef(rotated, minor_profile)[0, 1])
        if corr_minor > best_corr:
            best_corr = corr_minor
            best_key = f"{NOTE_NAMES[shift]} minor"

    return best_key


def _detect_chords(audio_path: str) -> list[dict[str, Any]]:
    import librosa
    import numpy as np

    y, sr = librosa.load(audio_path, sr=None)
    hop_length = 512
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)

    frame_duration = hop_length / sr
    segment_frames = int(0.5 / frame_duration)

    # Build all templates: (root, quality, 12-d vector)
    templates: list[tuple[str, str, np.ndarray]] = []
    for quality, base_vec in _CHORD_TEMPLATES.items():
        base = np.array(base_vec, dtype=float)
        for root_idx in range(12):
            rolled = np.roll(base, root_idx)
            root_name = NOTE_NAMES[root_idx]
            label = f"{root_name}{quality}" if quality != "" else root_name
            templates.append((root_name, label, rolled / np.linalg.norm(rolled)))

    chords: list[dict[str, Any]] = []
    num_segments = max(1, chroma.shape[1] // segment_frames)

    for seg_idx in range(num_segments):
        start = seg_idx * segment_frames
        end = min(start + segment_frames, chroma.shape[1])
        segment_chroma = np.mean(chroma[:, start:end], axis=1)
        seg_norm = np.linalg.norm(segment_chroma)
        if seg_norm < 1e-6:
            continue
        segment_chroma = segment_chroma / seg_norm

        best_sim = -1.0
        best_label = "N"
        for _, label, template in templates:
            sim = float(np.dot(segment_chroma, template))
            if sim > best_sim:
                best_sim = sim
                best_label = label

        time_sec = round(start * frame_duration, 2)

        # Deduplicate consecutive same chords
        if chords and chords[-1]["chord"] == best_label:
            continue

        chords.append({
            "time": time_sec,
            "chord": best_label,
            "confidence": round(best_sim, 3),
        })

    return chords


# ---------------------------------------------------------------------------
# Step E  -- MIDI notes -> guitar tab (greedy graph search)
# ---------------------------------------------------------------------------

def _midi_to_tab(
    note_events: list,
    tuning_name: str,
) -> dict[str, Any]:
    open_notes = TUNINGS.get(tuning_name, TUNINGS["standard"])

    prev_position = 5.0  # start mid-neck
    tab_notes: list[dict[str, Any]] = []

    for event in note_events:
        start_time = float(event[0])
        end_time = float(event[1])
        pitch = int(event[2])

        best_string = -1
        best_fret = -1
        best_cost = float("inf")

        for string_idx, open_note in enumerate(open_notes):
            fret = pitch - open_note
            if fret < 0 or fret > 22:
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

        if best_string < 0:
            continue

        # Exponential smoothing for position tracking
        prev_position = prev_position * 0.7 + best_fret * 0.3

        tab_notes.append({
            "time": round(start_time, 4),
            "duration": round(end_time - start_time, 4),
            "string": best_string,
            "fret": best_fret,
            "pitch": pitch,
        })

    return {
        "tuning": tuning_name,
        "open_notes": open_notes,
        "notes": tab_notes,
    }


# ---------------------------------------------------------------------------
# Step F  -- Smart Capo suggestion
# ---------------------------------------------------------------------------

def _transpose_chord_name(chord_name: str, semitones_down: int) -> str:
    """Transpose a chord name down by *semitones_down* semitones."""
    if not chord_name or chord_name == "N":
        return chord_name

    # Parse root
    if len(chord_name) > 1 and chord_name[1] in ("#", "b"):
        root = chord_name[:2]
        quality = chord_name[2:]
    else:
        root = chord_name[0]
        quality = chord_name[1:]

    # Handle flats -> sharps for lookup
    flat_to_sharp = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
    root = flat_to_sharp.get(root, root)

    if root not in NOTE_NAMES:
        return chord_name

    root_idx = NOTE_NAMES.index(root)
    new_idx = (root_idx - semitones_down) % 12
    return f"{NOTE_NAMES[new_idx]}{quality}"


def _suggest_capo(chords: list[dict[str, Any]]) -> int:
    best_capo = 0
    best_score = float("inf")

    for capo in range(8):
        score = capo * 0.5  # penalty for higher capo
        for chord_entry in chords:
            transposed = _transpose_chord_name(chord_entry["chord"], capo)
            difficulty = OPEN_CHORD_DIFFICULTY.get(transposed, 3)
            score += difficulty
        if score < best_score:
            best_score = score
            best_capo = capo

    return best_capo


# ---------------------------------------------------------------------------
# Step G  -- Roman Numeral analysis
# ---------------------------------------------------------------------------

def _roman_numeral_analysis(
    chords: list[dict[str, Any]],
    detected_key: str,
) -> list[dict[str, Any]]:
    from music21 import harmony
    from music21 import key as m21key
    from music21 import roman

    parts = detected_key.split()
    root = parts[0] if parts else "C"
    mode = parts[1] if len(parts) > 1 else "major"

    k = m21key.Key(root, mode)

    enriched: list[dict[str, Any]] = []
    for entry in chords:
        chord_name = entry["chord"]
        rn_str = ""
        try:
            cs = harmony.ChordSymbol(chord_name)
            rn = roman.romanNumeralFromChord(cs, k)
            rn_str = str(rn.figure)
        except Exception:
            rn_str = "?"

        enriched.append({
            **entry,
            "roman_numeral": rn_str,
        })

    return enriched


# ---------------------------------------------------------------------------
# Step H  -- Export GP5
# ---------------------------------------------------------------------------

def _export_gp5(
    tab_data: dict[str, Any],
    bpm: float,
    tuning_name: str,
) -> bytes:
    import guitarpro

    song = guitarpro.models.Song()
    song.tempo = int(bpm)
    song.title = "TabAI Transcription"
    song.artist = ""

    open_notes = TUNINGS.get(tuning_name, TUNINGS["standard"])

    # Create track
    track = song.tracks[0]
    track.name = "Guitar"
    track.channel.instrument = 25  # acoustic guitar (steel)
    track.isPercussionTrack = False

    # Set tuning strings
    track.strings = [
        guitarpro.models.GuitarString(number=i + 1, value=open_notes[i])
        for i in range(6)
    ]

    notes_list = tab_data.get("notes", [])
    if not notes_list:
        return _serialize_gp_song(song)

    # Group notes into measures (assume 4/4 time)
    beats_per_measure = 4
    seconds_per_beat = 60.0 / max(bpm, 30)
    seconds_per_measure = beats_per_measure * seconds_per_beat

    # Determine number of measures needed
    max_time = max(n["time"] for n in notes_list)
    num_measures = int(max_time / seconds_per_measure) + 2

    # Ensure song has enough measures
    while len(song.measureHeaders) < num_measures:
        header = guitarpro.models.MeasureHeader()
        header.tempo.value = int(bpm)
        header.timeSignature.numerator = 4
        header.timeSignature.denominator.value = 4
        song.measureHeaders.append(header)

        for t in song.tracks:
            measure = guitarpro.models.Measure(t, header)
            t.measures.append(measure)

    # Place notes into measures
    for note_entry in notes_list:
        t = note_entry["time"]
        string_num = note_entry["string"] + 1  # 1-indexed
        fret = note_entry["fret"]

        measure_idx = min(int(t / seconds_per_measure), num_measures - 1)

        measure = track.measures[measure_idx]
        voice = measure.voices[0]

        beat = guitarpro.models.Beat(voice)
        gp_note = guitarpro.models.Note(beat)
        gp_note.string = string_num
        gp_note.value = fret
        beat.notes.append(gp_note)
        voice.beats.append(beat)

    return _serialize_gp_song(song)


def _serialize_gp_song(song) -> bytes:
    import guitarpro

    buf = io.BytesIO()
    guitarpro.write(song, buf, versionTuple=(5, 10))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Step I  -- Export MIDI bytes
# ---------------------------------------------------------------------------

def _export_midi(midi_data) -> bytes:
    buf = io.BytesIO()
    midi_data.write(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

@app.function(
    gpu="L4",
    timeout=300,
    retries=1,
    memory=8192,
    secrets=[modal.Secret.from_name("tabai-secrets")],
)
async def run_transcription_pipeline(
    job_id: str,
    tuning: str = "standard",
) -> dict[str, Any]:
    """Execute the full transcription pipeline for a given job."""
    import asyncio

    tmp_dir = Path(f"/tmp/{job_id}")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ------------------------------------------------------------------
        # Step A -- Download audio from R2
        # ------------------------------------------------------------------
        await _update_job_status(job_id, "separating", "Downloading audio...", 5)

        audio_r2_key = await _get_job_audio_key(job_id)
        ext = audio_r2_key.rsplit(".", 1)[-1] if "." in audio_r2_key else "mp3"
        audio_path = str(tmp_dir / f"input.{ext}")
        audio_bytes = _download_from_r2(audio_r2_key)
        Path(audio_path).write_bytes(audio_bytes)

        # ------------------------------------------------------------------
        # Step B -- HTDemucs source separation
        # ------------------------------------------------------------------
        await _update_job_status(job_id, "separating", "Separating guitar stem...", 15)

        guitar_path = str(tmp_dir / "guitar.wav")
        _separate_guitar(audio_path, guitar_path)

        # ------------------------------------------------------------------
        # Step C -- Basic Pitch transcription
        # ------------------------------------------------------------------
        await _update_job_status(job_id, "transcribing", "Transcribing notes...", 40)

        model_output, midi_data, note_events = _transcribe_audio(guitar_path)

        # ------------------------------------------------------------------
        # Step D -- BPM, Key, Chord detection
        # ------------------------------------------------------------------
        await _update_job_status(job_id, "transcribing", "Analyzing music theory...", 55)

        bpm = _detect_bpm(guitar_path)
        detected_key = _detect_key(guitar_path)
        raw_chords = _detect_chords(guitar_path)

        # ------------------------------------------------------------------
        # Step E -- MIDI to guitar tab
        # ------------------------------------------------------------------
        await _update_job_status(job_id, "generating", "Generating tablature...", 65)

        if not note_events:
            tab_data = {"tuning": tuning, "open_notes": TUNINGS.get(tuning, TUNINGS["standard"]), "notes": []}
        else:
            tab_data = _midi_to_tab(note_events, tuning)

        # ------------------------------------------------------------------
        # Step F -- Smart Capo
        # ------------------------------------------------------------------
        capo = _suggest_capo(raw_chords)

        # ------------------------------------------------------------------
        # Step G -- Roman Numeral Analysis
        # ------------------------------------------------------------------
        await _update_job_status(job_id, "generating", "Harmonic analysis...", 75)

        chords_with_roman = _roman_numeral_analysis(raw_chords, detected_key)

        # ------------------------------------------------------------------
        # Step H -- Export GP5
        # ------------------------------------------------------------------
        await _update_job_status(job_id, "generating", "Exporting Guitar Pro...", 80)

        gp5_bytes = _export_gp5(tab_data, bpm, tuning)

        # ------------------------------------------------------------------
        # Step I -- Export MIDI
        # ------------------------------------------------------------------
        midi_bytes = _export_midi(midi_data)

        # ------------------------------------------------------------------
        # Step J -- Upload results to R2 and save transcription to DB
        # ------------------------------------------------------------------
        await _update_job_status(job_id, "generating", "Saving results...", 90)

        gp5_key = _upload_to_r2(gp5_bytes, f"results/{job_id}/tab.gp5")
        midi_key = _upload_to_r2(midi_bytes, f"results/{job_id}/transcription.mid")

        await _save_transcription(
            job_id,
            bpm=bpm,
            detected_key=detected_key,
            tuning=tuning,
            capo=capo,
            tab_data=tab_data,
            chords=chords_with_roman,
            gp5_r2_key=gp5_key,
            midi_r2_key=midi_key,
        )

        result_summary = {
            "bpm": round(bpm, 1),
            "key": detected_key,
            "capo": capo,
            "tuning": tuning,
            "chord_count": len(chords_with_roman),
            "note_count": len(tab_data.get("notes", [])),
            "gp5_r2_key": gp5_key,
            "midi_r2_key": midi_key,
        }

        await _set_job_result(job_id, result_summary)

        # ------------------------------------------------------------------
        # Step K -- Update job status to done
        # ------------------------------------------------------------------
        await _update_job_status(job_id, "done", "Complete", 100)

        return result_summary

    except Exception as exc:
        await _update_job_status(
            job_id, "error", f"Pipeline failed: {str(exc)[:200]}", 0
        )
        raise
    finally:
        # Clean up temp files
        import shutil

        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
