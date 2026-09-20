$ErrorActionPreference = "Stop"

Write-Host "=== Screen Translator - Windows setup ===" -ForegroundColor Cyan

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "[1/6] Checking Python 3.11..."
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
    Write-Host "Python 3.11 is not installed. Installing it with Python Install Manager..." -ForegroundColor Yellow
    & py install 3.11
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to install Python 3.11 automatically. Run 'py install 3.11' manually and retry."
    }
}

Write-Host "[2/6] Creating virtual environment..."
if (Test-Path ".venv") {
    Remove-Item -Recurse -Force ".venv"
}
& py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) {
    throw "Unable to create the Python 3.11 virtual environment."
}

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Write-Host "[3/6] Upgrading pip..."
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Unable to upgrade pip."
}

Write-Host "[4/6] Installing PaddlePaddle CPU..."
& $Python -m pip install "paddlepaddle==3.2.0" -i "https://www.paddlepaddle.org.cn/packages/stable/cpu/"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to install PaddlePaddle."
}

Write-Host "[5/6] Installing project dependencies..."
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Unable to install project dependencies."
}

Write-Host "[6/6] Verifying installation..."
& $Python -c "import sys, paddle; print('Python:', sys.version.split()[0]); print('PaddlePaddle:', paddle.__version__)"
if ($LASTEXITCODE -ne 0) {
    throw "PaddlePaddle verification failed."
}

Write-Host ""
Write-Host "Setup completed." -ForegroundColor Green
Write-Host "Activate the environment with:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Then start the app with:"
Write-Host "  python main.py"
