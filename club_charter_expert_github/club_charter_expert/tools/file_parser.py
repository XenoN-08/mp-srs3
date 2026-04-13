"""
Tool: File Parser
Extracts plain text from uploaded PDF or DOCX files.
"""
import io


def parse_uploaded_file(uploaded_file) -> str:
    """Extract text from a Streamlit UploadedFile object."""
    filename = uploaded_file.name.lower()
    raw_bytes = uploaded_file.read()

    if filename.endswith(".txt"):
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return raw_bytes.decode("latin-1", errors="replace")

    if filename.endswith(".pdf"):
        return _parse_pdf(raw_bytes)

    if filename.endswith(".docx"):
        return _parse_docx(raw_bytes)

    return ""


def _parse_pdf(raw_bytes: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            return "\n".join(
                page.extract_text() or "" for page in pdf.pages
            ).strip()
    except ImportError:
        pass

    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
        return "\n".join(p.extract_text() or "" for p in reader.pages).strip()
    except Exception:
        pass

    return "[Не удалось извлечь текст из PDF. Установите pdfplumber или pypdf.]"


def _parse_docx(raw_bytes: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(raw_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        return "[Не удалось извлечь текст из DOCX. Установите python-docx.]"
