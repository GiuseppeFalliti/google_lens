$ErrorActionPreference = "Stop"

Write-Host "=== Screen Translator - Windows setup ===" -ForegroundColor Cyan

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "[1/8] Checking Python 3.11..."
$python311Available = $false
try {
    & py -3.11 --version *> $null
    if ($LASTEXITCODE -eq 0) {
        $python311Available = $true
    }
} catch {
    $python311Available = $false
}

if (-not $python311Available) {
    Write-Host "Python 3.11 is not installed. Installing it..." -ForegroundColor Yellow
    & py install 3.11
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to install Python 3.11 automatically."
    }
}

Write-Host "[2/8] Creating/reusing virtual environment..."
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create the Python 3.11 virtual environment."
    }
} else {
    Write-Host "Existing .venv found; reusing it."
}

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Write-Host "[3/8] Upgrading pip..."
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Unable to upgrade pip."
}

Write-Host "[4/8] Removing the PaddleOCR 3/PaddleX stack..."
& $Python -m pip uninstall -y paddleocr paddlex modelscope modelscope-hub opencv-python opencv-contrib-python opencv-python-headless 2>$null
# pip uninstall returns non-zero when some optional packages do not exist; ignore it.

Write-Host "[5/8] Installing PaddlePaddle CPU 3.0.0..."
& $Python -m pip install --upgrade "paddlepaddle==3.0.0" -i "https://www.paddlepaddle.org.cn/packages/stable/cpu/"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to install PaddlePaddle 3.0.0."
}

Write-Host "[6/8] Installing project dependencies..."
& $Python -m pip install --upgrade -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Unable to install project dependencies."
}

Write-Host "[7/8] Pinning a stable CPU-only PyTorch for Argos..."
& $Python -m pip install --upgrade "torch==2.8.0" --index-url "https://download.pytorch.org/whl/cpu"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to install the CPU-only PyTorch build required by Argos."
}

Write-Host "[8/8] Verifying the two ML runtimes in separate processes..."
& $Python -c "import paddle; print('PaddlePaddle:', paddle.__version__)"
if ($LASTEXITCODE -ne 0) {
    throw "PaddlePaddle verification failed."
}

& $Python -c "from paddleocr import PaddleOCR; import paddleocr; print('PaddleOCR:', paddleocr.__version__)"
if ($LASTEXITCODE -ne 0) {
    throw "PaddleOCR verification failed."
}

& $Python -c "import torch; print('PyTorch for Argos:', torch.__version__)"
if ($LASTEXITCODE -ne 0) {
    throw "PyTorch/Argos runtime verification failed. Install/repair the Microsoft Visual C++ 2015-2022 x64 Redistributable and retry."
}

& $Python -c "import argostranslate; print('Argos Translate: OK')"
if ($LASTEXITCODE -ne 0) {
    throw "Argos Translate verification failed."
}

Write-Host ""
Write-Host "Setup completed." -ForegroundColor Green
Write-Host "IMPORTANT: PaddlePaddle OCR and Argos/PyTorch are intentionally run in separate processes."
Write-Host ""
Write-Host "Activate the environment with:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Then start the app with:"
Write-Host "  python main.py"
