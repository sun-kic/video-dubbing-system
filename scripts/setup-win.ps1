# Video Dubbing System - Windows + NVIDIA GPU Setup Script
# Tested on Windows 11 + RTX 3090 + CUDA 12.1
# Run in PowerShell as Administrator

Write-Host "=== Video Dubbing System - Windows CUDA Setup ===" -ForegroundColor Cyan

# 1. Check prerequisites
Write-Host "`n[1/7] Checking prerequisites..." -ForegroundColor Yellow

# Check Python 3.12
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "ERROR: Python not found. Download Python 3.12 from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "Make sure to check 'Add Python to PATH' during installation"
    exit 1
}
$pyVersion = python --version 2>&1
Write-Host "Python: $pyVersion"
if ($pyVersion -notmatch "3\.12") {
    Write-Host "WARNING: Python 3.12 recommended. Current version may have compatibility issues." -ForegroundColor Yellow
}

# Check CUDA
$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidiaSmi) {
    Write-Host "NVIDIA GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
} else {
    Write-Host "WARNING: nvidia-smi not found." -ForegroundColor Yellow
    Write-Host "Install CUDA 12.1: https://developer.nvidia.com/cuda-12-1-0-download-archive"
}

# Check ffmpeg
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Host "Installing ffmpeg via winget..." -ForegroundColor Yellow
    winget install Gyan.FFmpeg
    Write-Host "Please restart PowerShell after ffmpeg install and re-run this script" -ForegroundColor Yellow
    exit 0
}
Write-Host "ffmpeg: OK"

# 2. Redis via Docker
Write-Host "`n[2/7] Setting up Redis..." -ForegroundColor Yellow
$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) {
    $existing = docker ps -a --filter "name=redis-dubbing" --format "{{.Names}}" 2>$null
    if ($existing) {
        docker start redis-dubbing | Out-Null
        Write-Host "Redis: restarted existing container"
    } else {
        docker run -d --name redis-dubbing -p 6379:6379 --restart unless-stopped redis:7-alpine | Out-Null
        Write-Host "Redis: started new container"
    }
} else {
    Write-Host "Docker not found. Please install one of:" -ForegroundColor Yellow
    Write-Host "  A) Docker Desktop:        https://www.docker.com/products/docker-desktop"
    Write-Host "  B) Redis for Windows:     https://github.com/tporadowski/redis/releases"
    Write-Host "  C) WSL2 + Redis:          wsl --install, then: sudo apt install redis-server"
    Write-Host "After installing Redis, re-run this script." -ForegroundColor Yellow
    exit 1
}

# 3. Create virtual environment
Write-Host "`n[3/7] Creating Python virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host ".venv already exists, skipping"
} else {
    python -m venv .venv
    Write-Host "venv: OK"
}

# 4. Install PyTorch with CUDA first (must come before other packages)
Write-Host "`n[4/7] Installing PyTorch with CUDA 12.1 support..." -ForegroundColor Yellow
.venv\Scripts\pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --quiet
Write-Host "PyTorch CUDA: OK"

# 5. Install remaining dependencies
Write-Host "`n[5/7] Installing Python dependencies (first time may take 10-15 minutes)..." -ForegroundColor Yellow
.venv\Scripts\pip install --upgrade pip --quiet
.venv\Scripts\pip install --prefer-binary -r requirements-win-cuda.txt
Write-Host "Dependencies: OK"

# 6. Create .env
Write-Host "`n[6/7] Setting up environment config..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    # Windows CUDA defaults
    (Get-Content ".env") `
        -replace "WHISPER_BACKEND=faster-whisper", "WHISPER_BACKEND=faster-whisper" `
        -replace "WHISPER_DEVICE=cpu", "WHISPER_DEVICE=cuda" `
        -replace "WHISPER_COMPUTE_TYPE=int8", "WHISPER_COMPUTE_TYPE=float16" `
        -replace "DIARIZATION_DEVICE=cpu", "DIARIZATION_DEVICE=cuda" | Set-Content ".env"
    Write-Host ""
    Write-Host ">>> IMPORTANT: Edit .env and fill in:" -ForegroundColor Yellow
    Write-Host "    HF_TOKEN           - HuggingFace token (required for first run)"
    Write-Host "    TRANSLATION_API_KEY - OpenAI / OpenRouter key (optional)"
} else {
    Write-Host ".env already exists, skipping"
}

# 7. Create startup scripts
Write-Host "`n[7/7] Creating startup scripts..." -ForegroundColor Yellow

Set-Content "start-api.bat" @"
@echo off
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
.venv\Scripts\uvicorn backend.main:app --host 0.0.0.0 --port 8000
pause
"@

Set-Content "start-worker.bat" @"
@echo off
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
.venv\Scripts\celery -A backend.workers.celery_app.celery_app worker --loglevel=info --pool=solo
pause
"@

Write-Host "`n=== Setup Complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "=== First-Run Notes ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "These models will be downloaded automatically on first use:"
Write-Host "  - Whisper large-v3 (~3GB, via faster-whisper)"
Write-Host "  - pyannote speaker diarization (~300MB, requires HF_TOKEN + accepted terms)"
Write-Host "  - Demucs htdemucs (~300MB)"
Write-Host "  - F5-TTS F5TTS_v1_Base (~3GB)"
Write-Host ""
Write-Host "Accept pyannote model terms before first run:" -ForegroundColor Yellow
Write-Host "  https://huggingface.co/pyannote/speaker-diarization-3.1"
Write-Host "  https://huggingface.co/pyannote/segmentation-3.0"
Write-Host ""
Write-Host "=== How to Start ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Edit .env and add your HuggingFace token"
Write-Host "2. Double-click start-api.bat    (API server)"
Write-Host "3. Double-click start-worker.bat (Celery worker)"
Write-Host ""
Write-Host "=== Submit a Job (auto mode) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host '  curl -X POST http://localhost:8000/api/v1/dubbing/jobs `'
Write-Host '    -H "Content-Type: application/json" `'
Write-Host '    -d "{\"video_path\":\"C:/path/to/video.mp4\",\"target_language\":\"zh\",\"speaker_voice_map\":{}}"'
Write-Host ""
Write-Host "API docs: http://localhost:8000/api/v1/docs" -ForegroundColor Cyan
