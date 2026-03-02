# Video Dubbing System

A local AI-powered video dubbing pipeline. Automatically transcribes speech, translates dialogue, clones speakers' voices, and produces a dubbed video — all running on your own machine.

## Pipeline

```
Video → Extract Audio → ASR (Whisper) → Translation → Speaker Diarization
     → TTS Voice Cloning (F5-TTS) → Merge Audio → Mux with Video → Output
```

## Stack

| Component | Technology |
|-----------|-----------|
| API Server | FastAPI |
| Task Queue | Celery + Redis |
| ASR (Mac) | mlx-whisper — Apple Neural Engine |
| ASR (Windows) | faster-whisper — CUDA |
| Translation | GPT-5 (primary) / Helsinki-NLP offline (fallback) |
| Speaker Diarization | pyannote.audio |
| Voice Cloning TTS | F5-TTS |
| Video Processing | FFmpeg |
| Frontend | React + TypeScript (Vite) |

## Supported Platforms

| Platform | Hardware | Notes |
|----------|----------|-------|
| macOS | Apple Silicon M1/M2/M3 | MPS acceleration, `--pool=solo` required |
| Windows | NVIDIA GPU (RTX 3090 tested) | CUDA 12.1, full GPU acceleration |

---

## Prerequisites

### External Services

| Service | Required | Purpose | Get it |
|---------|----------|---------|--------|
| **HuggingFace Token** | **Yes** (first run) | Download pyannote diarization models | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |
| **OpenAI API Key** | No | High-quality GPT-5 translation | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |

> **HuggingFace model terms:** After obtaining your token, visit and accept the terms for:
> - https://huggingface.co/pyannote/speaker-diarization-3.1
> - https://huggingface.co/pyannote/segmentation-3.0
>
> **Note:** Once models are downloaded and cached, `HF_TOKEN` is no longer needed for subsequent runs.

> **Translation fallback:** If `OPENAI_API_KEY` is not set, the system automatically uses a free local Helsinki-NLP model (lower quality but no API cost).

### Local Dependencies

- Python **3.12**
- Redis
- FFmpeg

---

## Installation

### Mac Apple Silicon (M1 / M2 / M3)

```bash
# Clone the repository
git clone https://github.com/sun-kic/video-dubbing-system.git
cd video-dubbing-system

# Run the setup script (installs Python 3.12, Redis, ffmpeg, creates venv)
bash scripts/setup-mac.sh
```

The script will:
1. Install `python@3.12`, `redis`, `ffmpeg` via Homebrew
2. Create a `.venv` virtual environment
3. Install all dependencies
4. Create `.env` from `.env.example`

### Windows + NVIDIA GPU

```powershell
# Clone the repository
git clone https://github.com/sun-kic/video-dubbing-system.git
cd video-dubbing-system

# Run the setup script (Admin PowerShell recommended)
Set-ExecutionPolicy Bypass -Scope Process
.\scripts\setup-win.ps1
```

The script will:
1. Install `ffmpeg` via winget
2. Start Redis in a Docker container
3. Install PyTorch with CUDA 12.1
4. Install all dependencies
5. Create `.env` with CUDA settings pre-configured
6. Generate `start-api.bat` and `start-worker.bat` shortcuts

**CUDA 12.1 required.** Download from [NVIDIA CUDA Downloads](https://developer.nvidia.com/cuda-12-1-0-download-archive).

---

## Configuration

After installation, edit `.env` in the project root:

```env
# Required for first-time model download
HF_TOKEN=hf_your_token_here

# Optional: enables high-quality GPT-5 translation
# Falls back to free local Helsinki-NLP model if not set
OPENAI_API_KEY=sk-your_key_here

# ── Mac Apple Silicon (set automatically by setup-mac.sh) ──
WHISPER_BACKEND=mlx-whisper
WHISPER_MLX_MODEL=mlx-community/whisper-large-v3-mlx
DIARIZATION_DEVICE=cpu

# ── Windows NVIDIA GPU (set automatically by setup-win.ps1) ──
# WHISPER_BACKEND=faster-whisper
# WHISPER_DEVICE=cuda
# WHISPER_COMPUTE_TYPE=float16
# DIARIZATION_DEVICE=cuda
```

---

## Running the System

### Mac

Open two terminal windows:

**Terminal 1 — API Server:**
```bash
cd video-dubbing-system
PYTHONDONTWRITEBYTECODE=1 .venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 — Celery Worker:**
```bash
cd video-dubbing-system
PYTHONDONTWRITEBYTECODE=1 .venv/bin/celery -A backend.workers.celery_app.celery_app worker --loglevel=info --pool=solo
```

> `--pool=solo` is required on Apple Silicon. The MLX/Metal GPU context does not survive process forks.

### Windows

Double-click:
- `start-api.bat`
- `start-worker.bat`

---

## Usage

### 1. Prepare reference audio

Extract a 10-second clip of each speaker's voice (used for voice cloning):

```bash
# Extract speaker reference audio from the source video
ffmpeg -i input.mp4 -ss 10 -t 10 -ar 16000 -ac 1 ref_speaker0.wav
```

### 2. Submit a dubbing job

```bash
curl -X POST http://localhost:8000/api/v1/dubbing/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/absolute/path/to/input.mp4",
    "target_language": "zh",
    "speaker_voice_map": {
      "SPEAKER_00": "/absolute/path/to/ref_speaker0.wav",
      "SPEAKER_01": "/absolute/path/to/ref_speaker1.wav"
    }
  }'
```

Response:
```json
{
  "task_id": "abc123...",
  "status": "PENDING",
  "submitted_at": "2026-03-01T00:00:00"
}
```

### 3. Poll for progress

```bash
curl http://localhost:8000/api/v1/dubbing/jobs/{task_id}
```

```json
{
  "task_id": "abc123...",
  "status": "STARTED",
  "progress": 0.72,
  "message": "Synthesizing segment 42/150",
  "result": null
}
```

When `status` is `SUCCESS`, `result` contains the output path:

```json
{
  "status": "SUCCESS",
  "progress": 1.0,
  "result": {
    "output_video": "/tmp/video-dubbing/storage/dubbed_input_abc123.mp4",
    "transcript_segments": 150,
    "speakers_detected": ["SPEAKER_00", "SPEAKER_01"]
  }
}
```

### Supported target languages

`zh` (Chinese) · `en` (English) · `ja` (Japanese) · `ko` (Korean) · `es` (Spanish) · `fr` (French) · `de` (German) · `ru` (Russian) · `pt` (Portuguese) · `ar` (Arabic) · and more.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/dubbing/jobs` | Submit a dubbing job |
| `GET` | `/api/v1/dubbing/jobs/{task_id}` | Check job status and progress |
| `POST` | `/api/v1/voice-clone/synthesize` | Single TTS synthesis with voice cloning |
| `POST` | `/api/v1/media/upload` | Upload a video file |
| `GET` | `/health` | Health check |

Interactive API docs: `http://localhost:8000/api/v1/docs`

---

## Project Structure

```
video-dubbing-system/
├── backend/
│   ├── api/routes/         # FastAPI route handlers
│   ├── core/               # Config, logging
│   ├── models/             # Pydantic schemas
│   ├── services/
│   │   ├── asr.py          # Whisper ASR
│   │   ├── speaker_diarization.py  # pyannote
│   │   ├── translation.py  # GPT-4o / Helsinki-NLP
│   │   ├── tts.py          # F5-TTS voice cloning
│   │   └── video_processor.py  # FFmpeg
│   └── workers/            # Celery tasks
├── frontend/               # React + TypeScript UI
├── scripts/
│   ├── setup-mac.sh        # Mac setup script
│   └── setup-win.ps1       # Windows setup script
├── requirements-mac-m1.txt
├── requirements-win-cuda.txt
├── .env.example
└── docker-compose.yml
```

---

## Performance Reference

| Hardware | ASR (21 min video) | TTS per segment | Notes |
|----------|--------------------|-----------------|-------|
| M1 Mac mini 16GB | ~60-90 min | ~2 min | faster-whisper CPU only |
| M1 Pro Max 32GB | ~5-10 min | ~30 sec | mlx-whisper Neural Engine |
| RTX 3090 24GB | ~3-5 min | ~10 sec | faster-whisper CUDA |

---

## License

MIT
