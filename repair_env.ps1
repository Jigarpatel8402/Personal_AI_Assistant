Write-Host ""
Write-Host "================================="
Write-Host "   AI Assistant Environment"
Write-Host "================================="
Write-Host ""

Write-Host "[1/3] Activating virtual environment..."
& ".\.venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "[2/3] Repairing dependencies..."
python -m pip install -r requirements.txt

Write-Host ""
Write-Host "[3/3] Environment ready!"
Write-Host ""
