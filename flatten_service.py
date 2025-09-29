import fitz  # PyMuPDF
from fastapi import FastAPI, File, UploadFile, Response, HTTPException

app = FastAPI()

def flatten_pdf_bytes(pdf_bytes: bytes, dpi: int = 150) -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    new_doc = fitz.open()

    for page in doc:
        pix = page.get_pixmap(dpi=dpi)       # render page to image (your original method)
        rect = page.rect
        new_page = new_doc.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(rect, pixmap=pix)

    return new_doc.write()                    # return flattened PDF bytes

@app.get("/healthz")
def health():
    return {"ok": True}

@app.post("/flatten")
async def flatten_pdf(file: UploadFile = File(...)):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        # n8n sometimes sends "application/octet-stream" for files, so allow it
        raise HTTPException(status_code=400, detail="Upload a PDF file")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    flattened = flatten_pdf_bytes(pdf_bytes)  # dpi=150 by default (same as your code)

    return Response(
        content=flattened,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="flattened.pdf"'}
    )
