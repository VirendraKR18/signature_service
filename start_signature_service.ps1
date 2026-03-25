# Start Signature Detection Service
Write-Host "Starting Signature Detection Service on port 8001..." -ForegroundColor Green

# Check if model exists
$modelPath = "..\FastAPI\media\model\best.pt"
if (Test-Path $modelPath) {
    Write-Host "YOLO model found at: $modelPath" -ForegroundColor Green
} else {
    Write-Host "WARNING: YOLO model not found at: $modelPath" -ForegroundColor Yellow
    Write-Host "Signature detection will not be available" -ForegroundColor Yellow
}

# Start the service
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
