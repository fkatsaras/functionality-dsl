# PDF Report Generator Example

## Overview

Demonstrates handling `application/pdf` content type in FDSL. Shows how to:
- Accept JSON input for report generation
- Return PDF binary responses
- Handle metadata from external PDF services
- Download generated PDF files

## Use Case

A sales reporting system that generates PDF reports from sales data. The workflow:
1. Client sends sales data (JSON)
2. External service generates PDF and returns metadata
3. Client can download the PDF using the report ID

## Architecture

```
Client → [POST /api/reports/generate] → External PDF Service
                ↓
         Returns metadata (reportId, fileSize, etc.)
                ↓
Client → [GET /api/reports/{reportId}/download] → External PDF Service
                ↓
         Returns PDF binary
```

## Key Features

- **Content Type Handling**: `application/pdf` for binary responses
- **Two-step workflow**: Generate metadata first, then download PDF
- **Computed attributes**: Calculate file size in KB, generate download URLs
- **Error handling**: Validation for negative sales, invalid report IDs

## Files

- `main.fdsl` - API definition with PDF handling
- `dummy-service/` - Mock external PDF service (returns minimal valid PDFs)

## Running the Example

### 1. Generate the code
```bash
../../venv_WIN/Scripts/fdsl.exe generate main.fdsl --out generated
```

### 2. Start the generated app (creates network)
```bash
cd generated
docker compose -p thesis up --build
```

### 3. Start the dummy PDF service (joins network)
```bash
cd ../dummy-service
docker compose up --build
```

### 4. Test the endpoints

**Generate a report:**
```bash
curl -X POST http://localhost:8080/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "period": "Q4 2024",
      "totalSales": 125000.50,
      "totalOrders": 450,
      "topProduct": "Premium Widget",
      "revenue": 112500.45
    }
  }'
```

**Response:**
```json
{
  "reportId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "generatedAt": "2024-01-15T10:30:00",
  "fileSize": 407,
  "filename": "sales_report_Q4_2024.pdf",
  "fileSizeKB": 0.40,
  "downloadUrl": "/api/reports/a1b2c3d4-e5f6-7890-abcd-ef1234567890/download"
}
```

**Download the PDF:**
```bash
curl -X GET "http://localhost:8080/api/reports/{reportId}/download" \
  --output report.pdf
```

**Open the PDF:**
```bash
# Linux/Mac
open report.pdf

# Windows
start report.pdf
```

## Entity Flow

1. **SalesDataWrapper** → Input sales data (JSON)
2. **ReportMetadata** → Raw response from PDF service
3. **ReportInfo(ReportMetadata)** → Enhanced with computed fields:
   - `fileSizeKB` - File size converted to KB
   - `downloadUrl` - Constructed download URL
4. **PDFBinary** → Binary PDF wrapper for download

## Error Handling

- **400**: Negative sales values or invalid report ID format
- **404**: Report not found when downloading

## Learning Points

- Binary content type handling (`application/pdf`)
- Mixed content types (JSON request, PDF response)
- Two-endpoint workflows (create → download)
- Path parameter mapping for downloads
- Computed URLs and file size transformations

## Cleanup

```bash
bash ../../scripts/docker_cleanup.sh
```
