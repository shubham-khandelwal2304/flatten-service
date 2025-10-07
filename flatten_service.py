# app.py
import io
import fitz  # PyMuPDF
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import StreamingResponse

app = FastAPI()


def flatten_pdf_bytes(pdf_bytes: bytes, dpi: int = 150) -> bytes:
    """
    Rasterize each page at the requested DPI and reassemble as a new PDF.
    This guarantees a visually identical, fully-flattened PDF.
    """
    try:
        src = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or corrupted PDF")

    out = fitz.open()
    try:
        zoom = dpi / 72.0  # PDF user space is 72 DPI
        mat = fitz.Matrix(zoom, zoom)

        for page in src:
            # Rasterize (alpha=False to avoid transparency layers)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            # Convert to PNG bytes (robust across PyMuPDF versions)
            img = pix.tobytes("png")

            # Create a new page with the same size as the source page (points)
            new_page = out.new_page(width=page.rect.width, height=page.rect.height)
            # Place the raster image to cover the page
            new_page.insert_image(new_page.rect, stream=img)

        # Write final flattened PDF to memory
        buf = io.BytesIO()
        out.save(buf, deflate=True)
        buf.seek(0)
        return buf.read()
    finally:
        try:
            out.close()
        except Exception:
            pass
        try:
            src.close()
        except Exception:
            pass


@app.get("/healthz")
def health():
    return {"ok": True}


@app.post("/flatten")
async def flatten_pdf(
    file: UploadFile = File(..., description="PDF file to flatten"),
    dpi: int = Query(150, ge=72, le=600, description="Rasterization DPI (72–600)")
):
    # n8n may send 'application/pdf' or 'application/octet-stream'
    ct = (file.content_type or "").lower()
    if ct not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Upload a PDF file")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    flattened = flatten_pdf_bytes(data, dpi=dpi)

    # Return as a streamed PDF with a sensible filename
    filename = (file.filename or "document.pdf").rsplit(".pdf", 1)[0] + ".flattened.pdf"
    return StreamingResponse(
        io.BytesIO(flattened),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
