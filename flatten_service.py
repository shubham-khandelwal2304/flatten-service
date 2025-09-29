import fitz  # PyMuPDF
from fastapi import FastAPI, File, UploadFile, Response, HTTPException, Request

app = FastAPI()

def flatten_pdf_bytes(pdf_bytes: bytes, dpi: int = 150) -> bytes:
    """
    Render each page of the input PDF to an image at the given DPI,
    insert those images into a new PDF (one image per page),
    and return the new flattened PDF as bytes.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    new_doc = fitz.open()

    for page in doc:
        pix = page.get_pixmap(dpi=dpi)  # rasterize page
        rect = page.rect
        new_page = new_doc.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(rect, pixmap=pix)  # imprint image onto page

    return new_doc.write()  # bytes of the flattened PDF

@app.get("/healthz")
def health():
    return {"ok": True}

# ----- Option A: multipart/form-data upload (field name must be "file") -----
@app.post("/flatten")
async def flatten_pdf(file: UploadFile = File(...)):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        # n8n may use application/octet-stream for files
        raise HTTPException(status_code=400, detail="Upload a PDF file")
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    flattened = flatten_pdf_bytes(pdf_bytes)  # dpi=150 by default
    return Response(
        content=flattened,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="flattened.pdf"'}
    )

# ----- Option B: raw body upload (entire request body is the PDF) -----
@app.post("/flatten_raw")
async def flatten_pdf_raw(request: Request):
    ct = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if ct not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=415, detail="Send PDF as application/pdf")
    pdf_bytes = await request.body()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty body")

    flattened = flatten_pdf_bytes(pdf_bytes)
    return Response(
        content=flattened,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="flattened.pdf"'}
    )
