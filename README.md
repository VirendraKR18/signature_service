# Signature Detection Microservice

Isolated service for comprehensive signature detection with its own virtual environment to avoid numpy dependency conflicts between ultralytics and langchain.

## Features

### Visual Signature Detection (YOLO)
- Detects handwritten/drawn signatures using computer vision
- Provides bounding box coordinates and confidence scores
- Works on scanned documents and images

### Comprehensive Signature Analysis
- **Signature Field Presence**: Detects empty signature boxes/lines where signatures should go
- **Signed Borrower Names**: Extracts signer names from electronic signature text
- **Signature Types**: Identifies electronic, handwritten, and digital signatures
- **Empty Spaces**: Detects unfilled signature fields
- **Metadata Extraction**: Captures signature dates, labels, and context

## Setup

```bash
# Run setup script to create virtual environment and install dependencies
setup_env.bat
```

**Note**: Ensure Tesseract OCR is installed on your system for enhanced detection:
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Add to PATH or set TESSERACT_CMD in environment

## Run Service

```bash
# Start the signature detection service on port 8001
run_service.bat
```

## API Endpoints

### `GET /`
Service information and available endpoints

### `GET /health`
Health check and model status

### `POST /detect`
Detect visual signatures using YOLO model

**Request**: Multipart form with PDF file

**Response**:
```json
{
  "status": "success",
  "boxesByPage": {
    "1": [{"x1": 150, "y1": 800, "x2": 350, "y2": 900, "confidence": 0.95}]
  },
  "total_pages": 5,
  "pages_with_signatures": 2
}
```

### `POST /detect/comprehensive`
Comprehensive signature detection including fields, metadata, and types

**Request**: Multipart form with PDF file

**Response**:
```json
{
  "status": "success",
  "visual_signatures": {
    "1": [{"x1": 150, "y1": 800, "x2": 350, "y2": 900, "confidence": 0.95}]
  },
  "signature_fields": [
    {
      "page": 1,
      "field_type": "borrower_signature",
      "label": "Borrower Signature",
      "is_filled": false,
      "coordinates": {"x": 100, "y": 200, "width": 300, "height": 50},
      "nearby_text": "Date: ___________"
    }
  ],
  "signatures_detected": [
    {
      "page": 1,
      "signer_name": "John Doe",
      "signature_type": "electronic",
      "date": "03/11/2026",
      "coordinates": null
    }
  ],
  "summary": {
    "total_signature_fields": 5,
    "filled_fields": 2,
    "empty_fields": 3,
    "electronic_signatures": 1,
    "handwritten_signatures": 1
  }
}
```

## Integration

The main FastAPI application calls this service via HTTP to avoid dependency conflicts. Set `SIGNATURE_SERVICE_URL` environment variable in the main app to configure the endpoint (default: `http://localhost:8001`).

## Architecture

This microservice runs in an isolated virtual environment with:
- `numpy>=2.0` (required by ultralytics/opencv)
- `ultralytics>=8.0.0` (YOLO model)
- `opencv-python>=4.6.0` (image processing)
- `pytesseract>=0.3.10` (OCR for text extraction)

The main FastAPI application uses `numpy<2.0` (required by langchain), avoiding version conflicts.
