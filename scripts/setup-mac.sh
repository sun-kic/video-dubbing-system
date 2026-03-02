#!/bin/bash
# Video Dubbing System - Mac Apple Silicon Setup Script
# Tested on M1/M2/M3 Pro/Max with macOS 14+
set -e

echo "=== Video Dubbing System - Mac Setup ==="

# 1. Check prerequisites
echo ""
echo "[1/6] Checking prerequisites..."

if ! command -v brew &>/dev/null; then
  echo "ERROR: Homebrew not found. Install from https://brew.sh"
  exit 1
fi

if ! command -v python3.12 &>/dev/null; then
  echo "Installing Python 3.12..."
  brew install python@3.12
fi
echo "Python: $(python3.12 --version)"

if ! command -v ffmpeg &>/dev/null; then
  echo "Installing ffmpeg..."
  brew install ffmpeg
fi
echo "ffmpeg: $(ffmpeg -version 2>&1 | head -1)"

if ! command -v redis-cli &>/dev/null; then
  echo "Installing Redis..."
  brew install redis
fi

# 2. Start Redis
echo ""
echo "[2/6] Starting Redis..."
brew services start redis
sleep 1
redis-cli ping || { echo "ERROR: Redis failed to start"; exit 1; }
echo "Redis: OK"

# 3. Create virtual environment
echo ""
echo "[3/6] Creating Python 3.12 virtual environment..."
if [ -d ".venv" ]; then
  echo ".venv already exists, skipping"
else
  python3.12 -m venv .venv
  echo "venv: OK"
fi

# 4. Install dependencies
echo ""
echo "[4/6] Installing Python dependencies (first time may take 10-15 minutes)..."
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install --prefer-binary -r requirements-mac-m1.txt
echo "Dependencies: OK"

# 5. Create .env
echo ""
echo "[5/6] Setting up environment config..."
if [ ! -f .env ]; then
  cp .env.example .env
  # Mac Apple Silicon defaults
  sed -i '' 's/WHISPER_BACKEND=faster-whisper/WHISPER_BACKEND=mlx-whisper/' .env
  echo ""
  echo ">>> IMPORTANT: Edit .env and fill in:"
  echo "    HF_TOKEN         - HuggingFace token (required for first run)"
  echo "    TRANSLATION_API_KEY - OpenAI / OpenRouter key (optional, uses local model if not set)"
else
  echo ".env already exists, skipping"
fi

# 6. Done
echo ""
echo "[6/6] Setup complete!"
echo ""
echo "=== First-Run Notes ==="
echo ""
echo "The following models will be downloaded automatically on first use:"
echo "  - mlx-whisper (Whisper large-v3 MLX, ~1.5GB)"
echo "  - pyannote speaker diarization (~300MB, requires HF_TOKEN + accepted terms)"
echo "  - Demucs htdemucs (~300MB)"
echo "  - F5-TTS F5TTS_v1_Base (~3GB)"
echo ""
echo "Accept pyannote model terms before first run:"
echo "  https://huggingface.co/pyannote/speaker-diarization-3.1"
echo "  https://huggingface.co/pyannote/segmentation-3.0"
echo ""
echo "=== How to Start ==="
echo ""
echo "Terminal 1 — API server:"
echo "  cd $(pwd)"
echo "  PYTHONDONTWRITEBYTECODE=1 .venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "Terminal 2 — Celery worker:"
echo "  cd $(pwd)"
echo "  PYTHONDONTWRITEBYTECODE=1 .venv/bin/celery -A backend.workers.celery_app.celery_app worker --loglevel=info --pool=solo"
echo ""
echo "=== Submit a Job (auto mode — no manual setup needed) ==="
echo ""
echo '  curl -X POST http://localhost:8000/api/v1/dubbing/jobs \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '"'"'{"video_path":"/path/to/video.mp4","target_language":"zh","speaker_voice_map":{}}'"'"
echo ""
echo "API docs: http://localhost:8000/api/v1/docs"
