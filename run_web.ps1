# This script sets up the environment and launches the web UI and API.

# Stop on any error
$ErrorActionPreference = "Stop"

# --- 1. Find Python ---
$PythonExe = Get-Command -Name python -ErrorAction SilentlyContinue
if (-not $PythonExe) {
    $PythonExe = Get-Command -Name py -ErrorAction SilentlyContinue
}
if (-not $PythonExe) {
    Write-Error "Could not find 'python' or 'py' in your PATH. Please install Python 3.8+."
    exit 1
}
Write-Host "Using Python executable at $($PythonExe.Source)"

# --- 2. Create Virtual Environment ---
if (-not (Test-Path -Path ".\.venv")) {
    Write-Host "Creating Python virtual environment in .\.venv..."
    & $PythonExe -m venv .venv
    Write-Host "Virtual environment created."
} else {
    Write-Host "Virtual environment already exists."
}

# Define path to venv python
$VenvPython = ".\.venv\Scripts\python.exe"

# --- 3. Install Dependencies ---
Write-Host "Installing dependencies from requirements.txt..."
& $VenvPython -m pip install --upgrade pip -q
& $VenvPython -m pip install -r requirements.txt -q
Write-Host "Dependencies installed."

# --- 4. Launch Servers in the Background ---
Write-Host "Starting FastAPI server on http://127.0.0.1:8000..."
Start-Process -FilePath $VenvPython -ArgumentList "-m uvicorn", "server:app", "--host", "127.0.0.1", "--port", "8000"

Write-Host "Starting static file server on http://127.0.0.1:8080..."
# Change directory into 'static' to serve files from there.
$script = "cd static; $($using:VenvPython) -m http.server 8080"
Start-Process -FilePath "powershell" -ArgumentList "-Command", $script

# --- 5. Open Browser ---
$url = "http://127.0.0.1:8080/index.html"
Write-Host "Waiting a moment for servers to start..."
Start-Sleep -Seconds 3
Write-Host "Opening $url in your default browser."
Start-Process $url

Write-Host "Setup complete. The API and web server are running in the background."
