"""Text extraction for multiple document formats, used before indexing."""

from pathlib import Path

from pypdf import PdfReader

from src import config
from src.exceptions import RAGError, exception_handler, validate_rag_file_size


_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".log",
}


@exception_handler("rag.text_extraction.extract")
def extract_text(filepath: Path) -> str:
    """Extract plain text from a file, based on its extension.

    Supports:
    .txt/.md/.csv/.json/.yaml/.yml/.log
    .pdf
    .docx
    """

    filepath = validate_rag_file_size(filepath, max_size_mb=config.MAX_RAG_FILE_SIZE_MB)
    ext = filepath.suffix.lower()

    if not filepath.exists():
        raise RAGError(
            f"File not found: '{filepath}'.",
            user_message=f"File not found: {filepath}",
        )

    if not filepath.is_file():
        raise RAGError(
            f"Path is not a file: '{filepath}'.",
            user_message=f"Path is not a file: {filepath}",
        )

    if ext in _TEXT_EXTENSIONS:
        try:
            return filepath.read_text(
                encoding="utf-8",
            )

        except (OSError, UnicodeDecodeError) as exc:
            raise RAGError(
                f"Failed to read text file '{filepath}': {exc}",
                user_message=(
                    f"Could not read '{filepath.name}'."
                ),
            ) from exc

    if ext == ".pdf":
        return _extract_pdf_text(filepath)

    if ext == ".docx":
        try:
            import docx
            document = docx.Document(
                str(filepath)
            )

            return "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
            )

        except Exception as exc:
            raise RAGError(
                f"Failed to extract text from DOCX "
                f"'{filepath}': {exc}",
                user_message=(
                    f"Could not extract text from "
                    f"'{filepath.name}'."
                ),
            ) from exc

    raise RAGError(
        f"Unsupported file type '{ext}' for "
        f"'{filepath.name}'. "
        f"Supported: {sorted(_TEXT_EXTENSIONS)} + "
        f".pdf, .docx",
        user_message=(
            f"Unsupported file type '{ext}'. "
            f"Supported formats: "
            f"{', '.join(sorted(_TEXT_EXTENSIONS))}, "
            f".pdf, .docx."
        ),
    )


def _extract_pdf_text(filepath: Path) -> str:
    """Extract text from a PDF, using OCR when necessary."""

    try:
        reader = PdfReader(str(filepath))

        text = "\n\n".join(
            page.extract_text() or ""
            for page in reader.pages
        ).strip()

        if text:
            return text

    except Exception as exc:
        raise RAGError(
            f"Failed to extract text from PDF "
            f"'{filepath}': {exc}",
            user_message=(
                f"Could not read PDF "
                f"'{filepath.name}'."
            ),
        ) from exc

    return _extract_pdf_with_ocr(filepath)


def _extract_pdf_with_ocr(filepath: Path) -> str:
    """Extract text from a scanned PDF using OCR."""

    try:
        import pymupdf
        import pytesseract
        document = pymupdf.open(str(filepath))

        pages_text: list[str] = []

        for page in document:
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(2, 2)
            )

            image = pixmap.tobytes(
                "png"
            )

            from PIL import Image
            from io import BytesIO

            pil_image = Image.open(
                BytesIO(image)
            )

            text = pytesseract.image_to_string(
                pil_image
            ).strip()

            if text:
                pages_text.append(text)

        document.close()

    except Exception as exc:
        raise RAGError(
            f"Failed to OCR PDF "
            f"'{filepath}': {exc}",
            user_message=(
                f"Could not extract text from "
                f"'{filepath.name}' using OCR. "
                f"Make sure Tesseract OCR is installed."
            ),
        ) from exc

    result = "\n\n".join(
        pages_text
    ).strip()

    if not result:
        raise RAGError(
            f"No content could be extracted from "
            f"PDF '{filepath.name}'.",
            user_message=(
                f"No readable text was found in "
                f"'{filepath.name}'."
            ),
        )

    return result