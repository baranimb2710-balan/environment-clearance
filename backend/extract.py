"""
PDF text extraction module using PyMuPDF (fitz).
Extracts text page-by-page with clear boundary markers.
Detects scanned/image-only PDFs where no digital text layer exists.
"""
from typing import Tuple, Union, BinaryIO
import pymupdf as fitz  # PyMuPDF


def extract_text(pdf_file: Union[BinaryIO, bytes, str]) -> Tuple[str, int]:
    """
    Extracts text page-by-page from a PDF using PyMuPDF.

    Parameters:
        pdf_file: Streamlit UploadedFile, bytes buffer, or path string.

    Returns:
        Tuple[str, int]:
            - Full extracted text with '--- Page X ---' headers.
            - Total page count.
            Returns ("", page_count) if the PDF is scanned or lacks extractable digital text.
    """
    if hasattr(pdf_file, "getvalue"):
        pdf_bytes = pdf_file.getvalue()
    elif hasattr(pdf_file, "read"):
        pdf_bytes = pdf_file.read()
        if hasattr(pdf_file, "seek"):
            pdf_file.seek(0)
    elif isinstance(pdf_file, bytes):
        pdf_bytes = pdf_file
    elif isinstance(pdf_file, str):
        with open(pdf_file, "rb") as f:
            pdf_bytes = f.read()
    else:
        raise ValueError("Unsupported PDF file format provided to extract_text.")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)
    page_chunks = []
    total_characters = 0

    for idx in range(total_pages):
        page = doc[idx]
        page_num = idx + 1
        raw_text = page.get_text("text").strip()
        total_characters += len(raw_text)
        page_chunks.append(f"--- Page {page_num} ---\n{raw_text}")

    doc.close()

    # If the text is negligible (scanned/image-only PDF), return empty string
    if total_characters < 50:
        return "", total_pages

    full_text = "\n\n".join(page_chunks)
    return full_text, total_pages
