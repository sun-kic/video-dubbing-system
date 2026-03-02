# Video Dubbing System

A local AI-powered video dubbing pipeline. Automatically separates speech from background audio, transcribes and translates dialogue, clones each speaker's voice, and produces a dubbed video — all running on your own machine with no cloud required (except optional translation API).

## Pipeline

```
Video
 └─ Extract Audio
      └─ Demucs ──→ vocals.wav  → ASR → Translation → Speaker Diarization
               └─→ no_vocals.wav (BGM / SFX / ambience)        ↓
                        ↑                        Auto-extract speaker refs
                        │                                       ↓
                        │                         F5-TTS Voice Cloning
                        │                         (one model per speaker)
                        │                                       ↓
                        └────── pydub mix (TTS at original timestamps) ──→ Mux → Output
```

**Key features:**
- Background music, sound effects and ambience are **fully preserved**
- Each dubbed segment is placed at its **original timestamp** (lip-sync aligned)
- **Multi-speaker** support: automatically detects and clones every character's voice
- `speaker_voice_map: {}` — zero manual setup, fully automatic

## Stack

| Component | Technology |
|-----------|-----------|
| API Server | FastAPI |
| Task Queue | Celery + Redis |
| Vocal Separation | Demucs `htdemucs` — separates speech from BGM/SFX |
| ASR (Mac) | mlx-whisper — Apple Neural Engine acceleration |
| ASR (Windows) | faster-whisper — CUDA acceleration |
| Translation | GPT-5 (primary) / Helsinki-NLP offline (fallback) |
| Speaker Diarization | pyannote.audio |
| Voice Cloning TTS | F5-TTS |
| Audio Mixing | pydub — TTS positioned at original timestamps + background mixed in |
| Video Processing | FFmpeg |
| Frontend | React + TypeScript (Vite) |

## Supported Platforms

| Platform | Hardware | Notes |
|----------|----------|-------|
| macOS | Apple Silicon M1/M2/M3 Pro/Max | MPS acceleration, `--pool=solo` required |
| Windows | NVIDIA GPU (RTX 3090 tested) | CUDA 12.1, full GPU acceleration |

---

## Prerequisites

### External Services

| Service | Required | Purpose | Get it |
|---------|----------|---------|--------|
| **HuggingFace Token** | **Yes** (first run) | Download pyannote diarization models | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |
| **Translation API Key** | No | GPT-5 / DeepSeek / any LLM translation | OpenAI / OpenRouter / Ollama |

> **HuggingFace model terms:** After obtaining your token, accept terms at:
> - https://huggingface.co/pyannote/speaker-diarization-3.1
> - https://huggingface.co/pyannote/segmentation-3.0
>
> Once models are cached locally, `HF_TOKEN` is no longer needed for subsequent runs.

> **Translation fallback:** If no API key is set, the system automatically uses a free local Helsinki-NLP model.

### Models Downloaded on First Run

| Model | Size | Purpose |
|-------|------|---------|
| Demucs `htdemucs` | ~300 MB | Vocal / background separation |
| Whisper large-v3 (MLX or CTranslate2) | ~1.5–3 GB | Speech recognition |
| pyannote speaker-diarization-3.1 | ~300 MB | Speaker detection |
| F5-TTS `F5TTS_v1_Base` | ~3 GB | Voice cloning TTS |

### System Dependencies

- Python **3.12**
- Redis
- FFmpeg

---

## Installation

### Mac Apple Silicon (M1 / M2 / M3)

```bash
git clone https://github.com/sun-kic/video-dubbing-system.git
cd video-dubbing-system
bash scripts/setup-mac.sh
```

The script will:
1. Install `python@3.12`, `redis`, `ffmpeg` via Homebrew (if missing)
2. Create `.venv` with Python 3.12
3. Install all dependencies (including Demucs, pydub, mlx-whisper, F5-TTS)
4. Create `.env` with Apple Silicon defaults (`WHISPER_BACKEND=mlx-whisper`)

### Windows + NVIDIA GPU

```powershell
git clone https://github.com/sun-kic/video-dubbing-system.git
cd video-dubbing-system
Set-ExecutionPolicy Bypass -Scope Process
.\scripts\setup-win.ps1
```

The script will:
1. Install `ffmpeg` via winget (if missing)
2. Start Redis in a Docker container
3. Install PyTorch with CUDA 12.1
4. Install all dependencies (including Demucs, pydub, F5-TTS)
5. Create `.env` with CUDA defaults
6. Generate `start-api.bat` and `start-worker.bat`

**CUDA 12.1 required.** Download from [NVIDIA CUDA Downloads](https://developer.nvidia.com/cuda-12-1-0-download-archive).

---

## Configuration

Edit `.env` after installation:

```env
# Required for first-time pyannote model download
HF_TOKEN=hf_your_token_here

# ── Translation (optional — any OpenAI-compatible API) ──────────────────────
# OpenAI:
TRANSLATION_MODEL=gpt-5
TRANSLATION_BASE_URL=
TRANSLATION_API_KEY=sk-your_openai_key

# OpenRouter + DeepSeek (example):
# TRANSLATION_MODEL=deepseek/deepseek-chat-v3-5
# TRANSLATION_BASE_URL=https://openrouter.ai/api/v1
# TRANSLATION_API_KEY=sk-or-your_openrouter_key

# Local Ollama (example):
# TRANSLATION_MODEL=llama3
# TRANSLATION_BASE_URL=http://localhost:11434/v1
# TRANSLATION_API_KEY=ollama

# ── Mac Apple Silicon (set automatically by setup-mac.sh) ───────────────────
WHISPER_BACKEND=mlx-whisper
WHISPER_MLX_MODEL=mlx-community/whisper-large-v3-mlx
DIARIZATION_DEVICE=cpu

# ── Windows NVIDIA GPU (set automatically by setup-win.ps1) ─────────────────
# WHISPER_BACKEND=faster-whisper
# WHISPER_DEVICE=cuda
# WHISPER_COMPUTE_TYPE=float16
# DIARIZATION_DEVICE=cuda
```

---

## Running the System

### Mac

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

> `--pool=solo` is required on Apple Silicon — the MLX/Metal GPU context does not survive process forks.

### Windows

Double-click:
- `start-api.bat`
- `start-worker.bat`

---

## Usage

### Auto mode (recommended)

Pass an empty `speaker_voice_map: {}`. The system will automatically:
1. Separate vocals from background audio (Demucs)
2. Detect how many speakers are in the video (pyannote)
3. Find each speaker's longest clean segment (~10s) for voice cloning
4. Transcribe, translate, synthesize and mix the final dubbed video

```bash
curl -X POST http://localhost:8000/api/v1/dubbing/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/absolute/path/to/input.mp4",
    "target_language": "zh",
    "speaker_voice_map": {}
  }'
```

### Manual mode (custom reference audio)

Provide your own reference WAV for each speaker to control the cloned voice:

```bash
# Extract reference clips from specific timestamps
ffmpeg -i input.mp4 -ss 10 -t 10 -ar 16000 -ac 1 ref_speaker0.wav
ffmpeg -i input.mp4 -ss 120 -t 10 -ar 16000 -ac 1 ref_speaker1.wav

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

### Check progress

```bash
curl http://localhost:8000/api/v1/dubbing/jobs/{task_id}
```

```json
{
  "status": "STARTED",
  "progress": 0.65,
  "message": "Synthesizing segment 42/150"
}
```

When `status` is `SUCCESS`, `result.output_video` contains the output path.

### Supported target languages

`zh` · `en` · `ja` · `ko` · `es` · `fr` · `de` · `ru` · `pt` · `ar` · and more.

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
│   ├── api/routes/              # FastAPI route handlers
│   ├── core/                    # Config, logging
│   ├── models/                  # Pydantic schemas
│   ├── services/
│   │   ├── asr.py               # mlx-whisper / faster-whisper (dual backend)
│   │   ├── speaker_diarization.py  # pyannote.audio
│   │   ├── translation.py       # GPT-5 / OpenRouter / Ollama / Helsinki-NLP
│   │   ├── tts.py               # F5-TTS voice cloning
│   │   └── video_processor.py   # FFmpeg + Demucs + pydub mixing
│   └── workers/
│       └── tasks.py             # Full dubbing pipeline (Celery task)
├── frontend/                    # React + TypeScript UI
├── scripts/
│   ├── setup-mac.sh             # Mac one-click setup
│   └── setup-win.ps1            # Windows one-click setup
├── requirements-mac-m1.txt      # Mac dependencies
├── requirements-win-cuda.txt    # Windows CUDA dependencies
├── .env.example                 # Configuration template
└── docker-compose.yml
```

---

## Performance Reference

| Hardware | Demucs | ASR (21 min) | TTS per segment | Total (21 min) |
|----------|--------|--------------|-----------------|----------------|
| M1 Mac mini 16GB | ~3 min | ~60-90 min | ~2 min | ~10+ hrs |
| M1 Pro Max 32GB | ~1 min | ~5-10 min | ~30 sec | ~3-4 hrs |
| RTX 3090 24GB | ~1 min | ~3-5 min | ~10 sec | ~1-2 hrs |

---

## License

MIT
