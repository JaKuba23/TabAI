# TabAI

**AI-powered automatic music transcription for electric guitar.**

TabAI takes any audio file, isolates the guitar track using deep learning, transcribes the notes to MIDI, and generates playable guitar tablature complete with chord detection, key analysis, and smart capo suggestions. The result is rendered as an interactive tab player in the browser with playback controls and downloadable Guitar Pro / MIDI files.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Transcription Pipeline](#transcription-pipeline)
- [Backend API](#backend-api)
- [Frontend](#frontend)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [Running Locally](#running-locally)
- [Testing](#testing)
- [Deployment](#deployment)

---

## How It Works

```
Audio File (MP3/WAV/FLAC/M4A/OGG/AAC)
        |
        v
  [HTDemucs 6-Stem]  ------>  Isolate guitar track from full mix
        |
        v
  [Basic Pitch]      ------>  Transcribe audio to MIDI note events
        |
        v
  [Music Analysis]   ------>  Detect BPM, key, time signature, chords
        |
        v
  [Tab Generator]    ------>  Map MIDI pitches to guitar fretboard positions
        |
        v
  [Smart Capo]       ------>  Suggest optimal capo position for easier playing
        |
        v
  [Export]            ------>  Generate Guitar Pro 5 (.gp5) + MIDI (.mid) files
        |
        v
  [alphaTab Player]  ------>  Render interactive tablature in the browser
```

---

## Architecture

```
                        +-------------------+
                        |    Next.js 14     |
                        |    Frontend       |
                        | (TypeScript/React)|
                        +--------+----------+
                                 |
                         REST / WebSocket
                                 |
                        +--------v----------+
                        |    FastAPI         |
                        |    Backend         |
                        | (Python 3.11)     |
                        +---+----------+----+
                            |          |
                   +--------v--+  +----v---------+
                   | Supabase  |  | Cloudflare   |
                   | PostgreSQL|  | R2 Storage   |
                   +-----------+  +--------------+
                            |
                   +--------v----------+
                   |  Modal.com        |
                   |  GPU Worker (L4)  |
                   |  - HTDemucs       |
                   |  - Basic Pitch    |
                   |  - Music Theory   |
                   |  - GP5 Export     |
                   +-------------------+
```

- **Frontend** uploads audio, displays real-time progress via WebSocket, and renders results with an interactive tab player.
- **Backend** validates uploads, stores files in R2, creates job records in PostgreSQL, and dispatches GPU workers.
- **GPU Worker** runs the entire transcription pipeline on a Modal L4 GPU instance, updates job status in the database, and uploads results to R2.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS | UI and routing |
| Tab Rendering | alphaTab | Interactive tablature display and MIDI playback |
| State Management | Zustand | Client-side state |
| Backend | FastAPI, async SQLAlchemy, Pydantic v2 | REST API and WebSocket |
| Database | Supabase (PostgreSQL) | Job tracking, user accounts, transcription results |
| Object Storage | Cloudflare R2 (S3-compatible) | Audio files and generated outputs |
| GPU Compute | Modal.com (NVIDIA L4) | Source separation and transcription |
| Source Separation | HTDemucs 6-stem (Meta Research) | Isolate guitar from full mix |
| Audio-to-MIDI | Basic Pitch (Spotify Research) | Note transcription |
| Music Theory | librosa, music21 | BPM, key, chord, and harmonic analysis |
| Tab Export | pyguitarpro | Guitar Pro 5 file generation |
| Infrastructure | Docker Compose | Local development environment |

---

## Project Structure

```
tabai/
├── backend/
│   ├── api/
│   │   ├── config.py              # Pydantic settings from .env
│   │   ├── database.py            # Async SQLAlchemy engine & session factory
│   │   ├── main.py                # FastAPI app factory (CORS, GZip, routers, health check)
│   │   ├── models.py              # SQLAlchemy ORM models (User, Job, Transcription)
│   │   ├── storage.py             # Cloudflare R2 client (upload, download, presigned URLs)
│   │   ├── routes/
│   │   │   ├── jobs.py            # REST endpoints: upload, status, result, delete
│   │   │   └── ws.py              # WebSocket endpoint for real-time job progress
│   │   └── schemas/               # Pydantic request/response schemas (planned)
│   ├── workers/
│   │   └── transcription.py       # Modal GPU worker — full transcription pipeline
│   ├── core/                      # Domain logic modules (audio, tab, theory)
│   ├── tests/
│   │   ├── conftest.py            # Pytest fixtures
│   │   └── test_pipeline.py       # Unit tests for capo, transpose, tab generation, tunings
│   ├── scripts/
│   │   └── push-modal-secret.sh   # Push .env to Modal secrets
│   ├── dbutil.py                  # asyncpg SSL connection helper for Supabase
│   ├── Dockerfile                 # Production container image
│   └── requirements.txt           # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx         # Root layout (Inter font, dark theme)
│   │   │   ├── page.tsx           # Main page (upload → progress → result flow)
│   │   │   └── globals.css        # Tailwind directives and scrollbar styles
│   │   ├── components/
│   │   │   ├── upload/
│   │   │   │   ├── DropZone.tsx       # Drag-and-drop audio file selector
│   │   │   │   ├── TuningSelector.tsx # Guitar tuning dropdown
│   │   │   │   └── ProgressSteps.tsx  # Pipeline progress with animated steps
│   │   │   ├── player/
│   │   │   │   └── TabPlayer.tsx      # alphaTab-based interactive tab player
│   │   │   └── tabs/
│   │   │       ├── ChordProgression.tsx  # Scrollable chord card row with roman numerals
│   │   │       └── MetadataBar.tsx       # Key, BPM, tuning, capo pill badges
│   │   └── lib/
│   │       ├── types.ts           # TypeScript interfaces and type definitions
│   │       └── api.ts             # API client (REST + WebSocket + polling fallback)
│   ├── package.json
│   ├── tsconfig.json              # Strict TypeScript configuration
│   ├── tailwind.config.js
│   ├── next.config.js             # API proxy rewrites to backend
│   └── postcss.config.js
└── infra/
    └── docker-compose.yml         # Local dev: API + Redis + PostgreSQL
```

---

## Transcription Pipeline

The GPU worker (`backend/workers/transcription.py`) executes an 11-step pipeline on Modal's serverless infrastructure:

### Step A — Audio Download
Downloads the uploaded audio file from Cloudflare R2 to the worker's local filesystem.

### Step B — Source Separation (HTDemucs)
Uses Meta's **HTDemucs 6-stem model** to separate the audio into individual instrument tracks. The guitar stem is extracted and saved as a WAV file. Handles mono-to-stereo conversion and sample rate resampling automatically.

### Step C — Note Transcription (Basic Pitch)
Spotify's **Basic Pitch** model transcribes the isolated guitar audio into MIDI note events with configurable thresholds:
- Onset threshold: 0.5
- Frame threshold: 0.3
- Frequency range: 80 Hz — 1400 Hz (covers guitar's full range)
- Melodia trick enabled for improved monophonic pitch tracking

### Step D — Music Theory Analysis
- **BPM**: `librosa.beat.beat_track` with automatic tempo estimation
- **Key Detection**: Chroma CQT features correlated against Krumhansl-Schmuckler major/minor key profiles across all 12 roots
- **Chord Detection**: Chroma template matching every 0.5 seconds against 96 chord templates (12 roots x 8 qualities: major, minor, 7th, m7, maj7, dim, sus2, sus4). Consecutive duplicate chords are deduplicated.

### Step E — Fretboard Mapping
Maps each MIDI note to a guitar string/fret position using a cost-based optimization:

```
cost = fret × 0.1                        # prefer lower frets
     + string_index × 0.05               # prefer higher (thinner) strings
     + max(0, fret - 4) × 2.0            # penalize high positions
     + |fret - prev_position| × 0.15     # minimize hand movement
```

Hand position is tracked with exponential smoothing (`α = 0.3`) to produce natural fingering progressions.

**Supported tunings:**
| Name | Notes |
|------|-------|
| Standard | E A D G B e |
| Drop D | D A D G B e |
| Open G | D G D G B d |
| Half Step Down | Eb Ab Db Gb Bb Eb |
| Open E | E B E G# B e |

### Step F — Smart Capo Suggestion
Evaluates capo positions 0–7 by transposing all detected chords down by the capo amount and summing open chord difficulty scores (e.g., C=1, F=3, B=5) plus a position penalty (`capo × 0.5`). Returns the capo position with the lowest total score.

### Step G — Roman Numeral Analysis
Uses `music21` to assign roman numeral functions (I, IV, V, vi, etc.) to each detected chord relative to the song's key, enabling harmonic analysis.

### Step H — Guitar Pro Export
Generates a `.gp5` file using `pyguitarpro` with:
- Correct tempo and time signature
- 6-string guitar track with proper tuning values
- Notes placed into measures based on their timestamps

### Step I — MIDI Export
Exports the Basic Pitch MIDI data as a standard `.mid` file.

### Step J — Upload & Persist
Uploads GP5 and MIDI files to Cloudflare R2 and saves the full transcription record to the database (BPM, key, tuning, capo, tab data, chords with roman numerals, R2 keys).

### Step K — Complete
Sets job status to `done` with 100% progress.

---

## Backend API

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/jobs/upload` | Upload audio file with tuning selection. Returns `job_id`. |
| `GET` | `/api/jobs/{job_id}/status` | Poll current job status and progress percentage. |
| `GET` | `/api/jobs/{job_id}/result` | Get full transcription result with presigned download URLs. |
| `DELETE` | `/api/jobs/{job_id}` | Delete a job and its transcription. |
| `WS` | `/ws/jobs/{job_id}` | Real-time progress updates (polls DB every 1.5s). |
| `GET` | `/health` | Health check (`{"status": "ok", "version": "0.1.0"}`). |

### Job Status Flow

```
pending → uploading → separating → transcribing → generating → done
                                                              ↘ error
```

### Database Schema

Three tables managed by async SQLAlchemy with PostgreSQL:

- **users** — email, subscription status, monthly usage counter, Stripe customer ID
- **jobs** — processing status, progress, R2 storage keys, error messages, timestamps
- **transcriptions** — BPM, key, time signature, tuning, capo suggestion, tab data (JSONB), chord progression (JSONB), export file R2 keys

---

## Frontend

### Page Flow

1. **Upload** — Drag-and-drop or click to select an audio file. Choose guitar tuning from a dropdown. Click "Generate Tabs".
2. **Processing** — Real-time progress display with animated step indicators (Uploading → Isolating guitar → Transcribing → Generating tab → Done). Connected via WebSocket with automatic polling fallback.
3. **Result** — Interactive tab player powered by alphaTab with:
   - Play/pause with MIDI synthesis via built-in SoundFont
   - Speed control slider (25% — 150%)
   - Measure-by-measure cursor tracking
   - Download buttons for GP5 and MIDI files
   - Metadata bar showing detected key, BPM, tuning, and capo suggestion
   - Scrollable chord progression with roman numeral annotations

### Key Components

| Component | File | Description |
|-----------|------|-------------|
| `DropZone` | `components/upload/DropZone.tsx` | Drag-and-drop file input with validation and visual feedback |
| `TuningSelector` | `components/upload/TuningSelector.tsx` | Guitar tuning dropdown (5 tunings) |
| `ProgressSteps` | `components/upload/ProgressSteps.tsx` | Animated pipeline progress bar with step indicators |
| `TabPlayer` | `components/player/TabPlayer.tsx` | alphaTab integration with playback controls |
| `ChordProgression` | `components/tabs/ChordProgression.tsx` | Horizontal scrollable chord cards with time-based highlighting |
| `MetadataBar` | `components/tabs/MetadataBar.tsx` | Key, BPM, tuning, capo badge pills |

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16 (or Supabase account)
- [Modal](https://modal.com) account (for GPU workers)
- [Cloudflare R2](https://www.cloudflare.com/products/r2/) bucket

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

---

## Environment Variables

Copy `backend/.env.example` or create `backend/.env`:

```env
# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres

# Supabase
SUPABASE_URL=https://PROJECT.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Cloudflare R2
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=tabai-audio

# Application
SECRET_KEY=generate-with-openssl-rand-hex-32
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3001

# Optional
REDIS_URL=redis://localhost:6379
SENTRY_DSN=
```

### Modal Secrets

Push your `.env` values to Modal for the GPU worker:

```bash
cd backend
chmod +x scripts/push-modal-secret.sh
./scripts/push-modal-secret.sh
```

---

## Running Locally

### Option 1: Direct

```bash
# Terminal 1 — Backend
cd backend
source venv/bin/activate
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev

# Terminal 3 — Modal worker (requires Modal account)
cd backend
modal serve workers/transcription.py
```

- Frontend: http://localhost:3001
- Backend API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Option 2: Docker Compose

```bash
cd infra
docker compose up
```

Starts the API server, Redis, and PostgreSQL. The frontend and Modal worker still run separately.

---

## Testing

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

Test coverage includes:
- **Smart capo algorithm** — verifies G/C/D suggests capo 0, F/Bb suggests higher capo
- **Chord transposition** — G+2=A, Am-2=Gm, C+12=C, sharp/flat handling
- **Chord template generation** — all 96 templates (12 roots x 8 qualities) exist and are normalized
- **Tab generation** — fret range validation (0-22), no impossible stretches, position smoothing
- **Tuning validation** — all 5 tunings have 6 strings, MIDI values within 30-75, descending order

---

## Deployment

### Backend
Deploy the FastAPI app to any container platform (Fly.io, Railway, AWS ECS). The `Dockerfile` is production-ready.

### Frontend
Deploy to Vercel with the Next.js preset. Set the `NEXT_PUBLIC_WS_HOST` environment variable to point to your backend's WebSocket endpoint.

### GPU Worker
Deploy the Modal function:
```bash
cd backend
modal deploy workers/transcription.py
```

The worker scales to zero when idle and spins up L4 GPU instances on demand (cold start ~15s, processing ~30-60s per song).

---

## License

Proprietary. All rights reserved.
