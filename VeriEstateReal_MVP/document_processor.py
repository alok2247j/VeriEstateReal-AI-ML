"""Basic PDF/TXT text extraction and optional OCR for uploaded images."""
import re
ALLOWED_EXTENSIONS={"pdf","txt","png","jpg","jpeg"}
def allowed_file(filename): return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS
def extract_text(path,extension):
    ext=extension.lower().lstrip(".")
    if ext=="txt":
        with open(path,encoding="utf-8",errors="replace") as f: return f.read(),"Text file processed"
    if ext=="pdf":
        try:
            from pypdf import PdfReader
            text="\n".join((p.extract_text() or "") for p in PdfReader(path).pages).strip()
            return (text,"PDF text extracted") if text else ("","No selectable text found. For scanned PDFs, use OCR or a text-based sample PDF.")
        except Exception as e: return "",f"Could not read PDF: {e}"
    if ext in {"png","jpg","jpeg"}:
        try:
            from PIL import Image
            import pytesseract
            text=pytesseract.image_to_string(Image.open(path)).strip()
            return (text,"Image OCR completed") if text else ("","OCR did not find readable text")
        except Exception as e: return "",f"Optional image OCR is unavailable. Install Tesseract OCR separately. Details: {e}"
    return "","Unsupported file type"
def extract_fields(text):
    text=text or ""; lines=[s.strip() for s in text.splitlines() if s.strip()]; out={}
    patterns={"property_id":r"(?im)^\s*(?:property\s*id|plot\s*(?:no|number)|survey\s*(?:no|number)|registration\s*(?:no|number))\s*[:#\-]?\s*([A-Za-z0-9/\-]+)","locality":r"(?im)^\s*(?:locality|neighbourhood|neighborhood)\s*[:\-]\s*(.+)$","address":r"(?im)^\s*address\s*[:\-]\s*(.+)$","area_sqft":r"(?im)^\s*(?:built[- ]?up\s*)?area\s*[:\-]\s*([\d,]+(?:\.\d+)?)\s*(?:sq\.?\s*ft|sqft|square feet)?"}
    for k,p in patterns.items():
        m=re.search(p,text)
        if m: out[k]=m.group(1).strip()
    out['preview']="\n".join(lines[:12])[:1500]; return out

