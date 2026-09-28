"""Module containing file management functionality."""

from pathlib import Path

from src.exceptions import (
    ValidationError,
)


def validate_file(
    file_path: str,
    allowed_extensions: list[str],
) -> Path:
    """
    Validate a file path against allowed extensions.
    """

    file_path = file_path.strip().strip('"').strip("'")

    path = Path(file_path).expanduser()

    # -----------------------------------------
    # Check File Exists
    # -----------------------------------------

    if not path.exists():

        raise ValidationError(
            f"File does not exist: {file_path}",
            user_message=(
                "The specified file does not exist."
            ),
        )

    # -----------------------------------------
    # Check Is File
    # -----------------------------------------

    if not path.is_file():

        raise ValidationError(
            f"Path is not a file: {file_path}",
            user_message=(
                "The specified path is not a file."
            ),
        )

    # -----------------------------------------
    # Check Extension
    # -----------------------------------------

    extension = path.suffix.lower().lstrip(".")

    allowed = {
        item.lower().lstrip(".")
        for item in allowed_extensions
    }

    if extension not in allowed:

        allowed_text = ", ".join(
            sorted(allowed)
        )

        raise ValidationError(
            (
                f"Unsupported file extension: "
                f".{extension}. "
                f"Allowed: {allowed_text}"
            ),
            user_message=(
                f"Unsupported file type. "
                f"Allowed types: {allowed_text}."
            ),
        )

    return path


def extract_file_content(
    file_path: Path,
) -> str:
    """
    Extract text content from a supported file.
    """

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        import pymupdf
        import pytesseract
        from PIL import Image

        pytesseract.pytesseract.tesseract_cmd = (
            r"C:\Users\REl330\AppData\Local\Tesseract-OCR\tesseract.exe"
        )

        document = pymupdf.open(file_path)

        content = []

        for page in document:

            # -----------------------------------------
            # Try normal PDF text extraction
            # -----------------------------------------

            text = page.get_text("text")

            if text.strip():
                content.append(text)
                continue

            # -----------------------------------------
            # OCR fallback for image/scanned PDF
            # -----------------------------------------

            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(2, 2)
            )

            image = Image.frombytes(
                "RGB",
                [pixmap.width, pixmap.height],
                pixmap.samples,
            )

            ocr_text = pytesseract.image_to_string(
                image
            )

            if ocr_text.strip():
                content.append(ocr_text)

        document.close()

        return "\n\n".join(content)

    if extension == ".docx":
        from docx import Document

        document = Document(file_path)

        content = []

        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                content.append(paragraph.text)

        return "\n".join(content)

    raise ValidationError(
        f"Unsupported file type for extraction: {extension}",
        user_message=(
            f"File content extraction is not supported "
            f"for {extension} files."
        ),
    )