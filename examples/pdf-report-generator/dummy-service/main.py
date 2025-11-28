"""
Dummy PDF Service - Mock External PDF API/Database
Just returns pre-generated dummy PDF bytes to simulate an external service
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from datetime import datetime
from typing import Dict
import uuid

app = FastAPI(title="Dummy PDF Service")

# Mock "database" of stored PDFs (just dummy bytes)
pdf_storage: Dict[str, bytes] = {}


class SalesData(BaseModel):
    period: str
    totalSales: float
    totalOrders: int
    topProduct: str
    revenue: float


class SalesDataWrapper(BaseModel):
    data: SalesData


class ReportMetadata(BaseModel):
    reportId: str
    generatedAt: str
    fileSize: int
    filename: str


# Minimal valid PDF (just enough to be recognized as PDF)
DUMMY_PDF_BYTES = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Sales Report) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000314 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
407
%%EOF
"""


@app.post("/generate-report", response_model=ReportMetadata)
async def generate_report(wrapper: SalesDataWrapper):
    """Mock: Store sales data and return metadata (simulates DB insert)"""
    # Generate unique ID (like a database would)
    report_id = str(uuid.uuid4())

    # Store dummy PDF bytes (simulating PDF storage in DB)
    pdf_storage[report_id] = DUMMY_PDF_BYTES

    # Return metadata (what a real service would return after generating PDF)
    return ReportMetadata(
        reportId=report_id,
        generatedAt=datetime.now().isoformat(),
        fileSize=len(DUMMY_PDF_BYTES),
        filename=f"sales_report_{wrapper.data.period.replace(' ', '_')}.pdf"
    )


@app.get("/download/{reportId}")
async def download_report(reportId: str):
    """Mock: Retrieve PDF from storage (simulates DB query)"""
    if reportId not in pdf_storage:
        raise HTTPException(status_code=404, detail="Report not found")

    pdf_bytes = pdf_storage[reportId]

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=report_{reportId[:8]}.pdf"
        }
    )


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "stored_reports": len(pdf_storage)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
