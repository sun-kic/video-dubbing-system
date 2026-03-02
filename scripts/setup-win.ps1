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
    Write-Host "WARNING: Python 3.12 recommended. Current version may have issues." -ForegroundColor Yellow
}

# Check CUDA
$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidiaSmi) {
    Write-Host "NVIDIA GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
} else {
    Write-Host "WARNING: nvidia-smi not found. Install CUDA 12.1 from https://developer.nvidia.com/cuda-12-1-0-download-archive" -ForegroundColor Yellow
}

# Check ffmpeg
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Host "Installing ffmpeg via winget..."
    winget install Gyan.FFmpeg
    Write-Host "Please restart PowerShell after ffmpeg install and re-run this script"
    exit 0
}
Write-Host "ffmpeg: OK"

# 2. Redis via Docker
Write-Host "`n[2/7] Setting up Redis..." -ForegroundColor Yellow
$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) {
    docker run -d --name redis-dubbing -p 6379:6379 --restart unless-stopped redis:7-alpine
    Start-Sleep -Seconds 2
    Write-Host "Redis: started via Docker"
} else {
    Write-Host "Docker not found. Options:" -ForegroundColor Yellow
    Write-Host "  A) Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    Write-Host "  B) Install Redis for Windows: https://github.com/tporadowski/redis/releases"
    Write-Host "  C) Use WSL2 and run: sudo service redis-server start"
    Write-Host "Please install Redis and re-run this script."
    exit 1
}

# 3. Create virtual environment
Write-Host "`n[3/7] Creating Python virtual environment..." -ForegroundColor Yellow
python -m venv .venv
Write-Host "venv: OK"

# 4. Install PyTorch with CUDA first
Write-Host "`n[4/7] Installing PyTorch with CUDA 12.1 support..." -ForegroundColor Yellow
.venv\Scripts\pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
Write-Host "PyTorch CUDA: OK"

# 5. Install remaining dependencies
Write-Host "`n[5/7] Installing Python dependencies..." -ForegroundColor Yellow
.venv\Scripts\pip install --upgrade pip --quiet
.venv\Scripts\pip install --prefer-binary -r requirements-win-cuda.txt
Write-Host "Dependencies: OK"

# 6. Create .env
Write-Host "`n[6/7] Setting up environment config..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    # Override for CUDA
    (Get-Content ".env") -replace "WHISPER_DEVICE=cpu", "WHISPER_DEVICE=cuda" `
                         -replace "WHISPER_COMPUTE_TYPE=int8", "WHISPER_COMPUTE_TYPE=float16" `
                         -replace "DIARIZATION_DEVICE=cpu", "DIARIZATION_DEVICE=cuda" | Set-Content ".env"
    Write-Host ""
    Write-Host ">>> IMPORTANT: Edit .env and fill in:" -ForegroundColor Yellow
    Write-Host "    HF_TOKEN  - from https://huggingface.co/settings/tokens"
    Write-Host "    (OpenAI API key is optional)"
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
"@

Set-Content "start-worker.bat" @"
@echo off
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
.venv\Scripts\celery -A backend.workers.celery_app.celery_app worker --loglevel=info --pool=solo
"@

Write-Host "`n=== Setup Complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:"
Write-Host "1. Edit .env and add your HuggingFace token"
Write-Host "   Accept model terms at:"
Write-Host "   - https://huggingface.co/pyannote/speaker-diarization-3.1"
Write-Host "   - https://huggingface.co/pyannote/segmentation-3.0"
Write-Host ""
Write-Host "2. Start API server:    double-click start-api.bat"
Write-Host "3. Start Celery worker: double-click start-worker.bat"
Write-Host ""
Write-Host "4. Submit a test job:"
Write-Host '   curl -X POST http://localhost:8000/api/v1/dubbing/jobs `'
Write-Host '     -H "Content-Type: application/json" `'
Write-Host '     -d "{\"video_path\":\"C:/path/to/video.mp4\",\"target_language\":\"zh\",\"speaker_voice_map\":{\"SPEAKER_00\":\"C:/path/to/ref.wav\"}}"'
