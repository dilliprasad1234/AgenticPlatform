"""
MCP Connector — Local files & Windows filesystem.

Covers: PDF, Word (.docx), Excel (.xlsx), CSV, Markdown, PowerPoint (.pptx),
plain text, and generic folder / filesystem operations (list, create,
move, copy, delete) on local disk — including any Windows path
(C:\\Users\\... etc.) or network share the machine running this server
can see.

No external service credentials needed. Optionally set FILES_ROOT_DIR in
.env to give relative paths a default root; absolute paths always work
as given regardless of that setting.

Every underlying library here (pypdf, python-docx, openpyxl, python-pptx)
is synchronous, so each tool wraps its call in asyncio.to_thread — this
keeps the server non-blocking: a slow read of a large spreadsheet doesn't
stall other requests being handled concurrently.
"""

import argparse
import asyncio
import csv as csv_module
import io
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).resolve().parent / ".env")

mcp = FastMCP(
    name="files-connector",
    instructions=(
        "CRUD operations on local files (PDF, Word, Excel, CSV, Markdown, "
        "PowerPoint, plain text) and folders/filesystem paths."
    ),
)

FILES_ROOT_DIR = os.environ.get("FILES_ROOT_DIR", "").strip()


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute() and FILES_ROOT_DIR:
        p = Path(FILES_ROOT_DIR) / p
    return p


# --- Filesystem / folders (Local folders, Windows file system) -----------

@mcp.tool()
async def fs_list_dir(path: str) -> list:
    """List entries in a folder, with type (file/dir) and size."""
    def _run():
        p = _resolve(path)
        return [
            {"name": e.name, "type": "dir" if e.is_dir() else "file",
             "size": e.stat().st_size if e.is_file() else None}
            for e in sorted(p.iterdir())
        ]
    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_get_info(path: str) -> dict:
    """Get metadata (exists, type, size, modified time) for a path."""
    def _run():
        p = _resolve(path)
        if not p.exists():
            return {"exists": False, "path": str(p)}
        st = p.stat()
        return {
            "exists": True, "path": str(p), "type": "dir" if p.is_dir() else "file",
            "size": st.st_size, "modified": st.st_mtime,
        }
    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_create_dir(path: str) -> dict:
    """Create a folder (and any missing parent folders)."""
    def _run():
        p = _resolve(path)
        p.mkdir(parents=True, exist_ok=True)
        return {"created_dir": str(p)}
    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_move(src: str, dst: str) -> dict:
    """Move or rename a file/folder."""
    def _run():
        s, d = _resolve(src), _resolve(dst)
        shutil.move(str(s), str(d))
        return {"moved_to": str(d)}
    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_copy(src: str, dst: str) -> dict:
    """Copy a file (or a folder, recursively)."""
    def _run():
        s, d = _resolve(src), _resolve(dst)
        if s.is_dir():
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
        return {"copied_to": str(d)}
    return await asyncio.to_thread(_run)


@mcp.tool()
async def fs_delete(path: str, recursive: bool = False) -> dict:
    """Delete a file, or a folder (recursive=true required for non-empty folders). Irreversible."""
    def _run():
        p = _resolve(path)
        if p.is_dir():
            if recursive:
                shutil.rmtree(p)
            else:
                p.rmdir()
        else:
            p.unlink()
        return {"deleted": str(p)}
    return await asyncio.to_thread(_run)


# --- Plain text / Markdown ------------------------------------------------

@mcp.tool()
async def text_read(path: str) -> str:
    """Read a plain text or Markdown file's full content."""
    def _run():
        return _resolve(path).read_text(encoding="utf-8", errors="replace")
    return await asyncio.to_thread(_run)


@mcp.tool()
async def text_write(path: str, content: str, mode: str = "overwrite") -> dict:
    """Write to a plain text or Markdown file. mode: 'overwrite' (default, creates if missing) or 'append'."""
    def _run():
        p = _resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append":
            with p.open("a", encoding="utf-8") as f:
                f.write(content)
        else:
            p.write_text(content, encoding="utf-8")
        return {"written": str(p), "mode": mode}
    return await asyncio.to_thread(_run)


# --- CSV -------------------------------------------------------------------

@mcp.tool()
async def csv_read(path: str, max_rows: int = 100) -> list:
    """Read a CSV file as a list of row dicts (header row used as keys)."""
    def _run():
        p = _resolve(path)
        with p.open(newline="", encoding="utf-8", errors="replace") as f:
            reader = csv_module.DictReader(f)
            rows = []
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                rows.append(row)
            return rows
    return await asyncio.to_thread(_run)


@mcp.tool()
async def csv_write(path: str, rows: list[dict]) -> dict:
    """Create or overwrite a CSV file from a list of row dicts. Column order follows the first row's keys."""
    def _run():
        p = _resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not rows:
            p.write_text("", encoding="utf-8")
            return {"written": str(p), "rows": 0}
        with p.open("w", newline="", encoding="utf-8") as f:
            writer = csv_module.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return {"written": str(p), "rows": len(rows)}
    return await asyncio.to_thread(_run)


@mcp.tool()
async def csv_append_row(path: str, row: dict) -> dict:
    """Append one row to an existing CSV file."""
    def _run():
        p = _resolve(path)
        file_exists = p.exists() and p.stat().st_size > 0
        with p.open("a", newline="", encoding="utf-8") as f:
            writer = csv_module.DictWriter(f, fieldnames=list(row.keys()))
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
        return {"appended_to": str(p)}
    return await asyncio.to_thread(_run)


# --- PDF ---------------------------------------------------------------

@mcp.tool()
async def pdf_read_text(path: str, max_pages: int | None = None) -> str:
    """Extract text from a PDF (pages joined with form-feed markers). Won't work on scanned/image-only PDFs."""
    def _run():
        from pypdf import PdfReader
        reader = PdfReader(str(_resolve(path)))
        pages = reader.pages[:max_pages] if max_pages else reader.pages
        return "\n\x0c\n".join(p.extract_text() or "" for p in pages)
    return await asyncio.to_thread(_run)


@mcp.tool()
async def pdf_get_info(path: str) -> dict:
    """Get page count and basic metadata for a PDF."""
    def _run():
        from pypdf import PdfReader
        reader = PdfReader(str(_resolve(path)))
        meta = reader.metadata or {}
        return {"page_count": len(reader.pages), "title": meta.get("/Title"), "author": meta.get("/Author")}
    return await asyncio.to_thread(_run)


@mcp.tool()
async def pdf_create(path: str, pages: list[str]) -> dict:
    """Create a new PDF, one page of plain text per list entry."""
    def _run():
        from fpdf import FPDF
        p = _resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        pdf = FPDF()
        pdf.set_font("Helvetica", size=12)
        for text in pages:
            pdf.add_page()
            pdf.multi_cell(0, 8, text)
        pdf.output(str(p))
        return {"created": str(p), "pages": len(pages)}
    return await asyncio.to_thread(_run)


@mcp.tool()
async def pdf_append_page(path: str, text: str) -> dict:
    """Append a new text page to an existing PDF."""
    def _run():
        from fpdf import FPDF
        from pypdf import PdfReader, PdfWriter
        p = _resolve(path)

        new_page_pdf = FPDF()
        new_page_pdf.set_font("Helvetica", size=12)
        new_page_pdf.add_page()
        new_page_pdf.multi_cell(0, 8, text)
        new_bytes = io.BytesIO(new_page_pdf.output())

        writer = PdfWriter()
        for pg in PdfReader(str(p)).pages:
            writer.add_page(pg)
        for pg in PdfReader(new_bytes).pages:
            writer.add_page(pg)
        with p.open("wb") as f:
            writer.write(f)
        return {"appended_to": str(p)}
    return await asyncio.to_thread(_run)


# --- Word (.docx) --------------------------------------------------------

@mcp.tool()
async def docx_read(path: str) -> str:
    """Read all paragraph text from a Word document."""
    def _run():
        from docx import Document
        doc = Document(str(_resolve(path)))
        return "\n".join(p.text for p in doc.paragraphs)
    return await asyncio.to_thread(_run)


@mcp.tool()
async def docx_create(path: str, paragraphs: list[str], title: str | None = None) -> dict:
    """Create a new Word document from a list of paragraphs, with an optional heading."""
    def _run():
        from docx import Document
        p = _resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        doc = Document()
        if title:
            doc.add_heading(title, level=1)
        for para in paragraphs:
            doc.add_paragraph(para)
        doc.save(str(p))
        return {"created": str(p), "paragraphs": len(paragraphs)}
    return await asyncio.to_thread(_run)


@mcp.tool()
async def docx_append_paragraph(path: str, text: str) -> dict:
    """Append a paragraph to an existing Word document."""
    def _run():
        from docx import Document
        p = _resolve(path)
        doc = Document(str(p))
        doc.add_paragraph(text)
        doc.save(str(p))
        return {"appended_to": str(p)}
    return await asyncio.to_thread(_run)


@mcp.tool()
async def docx_replace_text(path: str, find: str, replace: str) -> dict:
    """Find-and-replace text across all paragraphs in a Word document."""
    def _run():
        from docx import Document
        p = _resolve(path)
        doc = Document(str(p))
        count = 0
        for para in doc.paragraphs:
            if find in para.text:
                for run in para.runs:
                    if find in run.text:
                        run.text = run.text.replace(find, replace)
                        count += 1
        doc.save(str(p))
        return {"replacements_made": count}
    return await asyncio.to_thread(_run)


# --- Excel (.xlsx) -------------------------------------------------------

@mcp.tool()
async def xlsx_read(path: str, sheet: str | None = None, max_rows: int = 100) -> list:
    """Read rows from an Excel sheet (default: active sheet)."""
    def _run():
        from openpyxl import load_workbook
        wb = load_workbook(str(_resolve(path)), read_only=True, data_only=True)
        ws = wb[sheet] if sheet else wb.active
        rows = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= max_rows:
                break
            rows.append(list(row))
        return rows
    return await asyncio.to_thread(_run)


@mcp.tool()
async def xlsx_create(path: str, rows: list[list], sheet_name: str = "Sheet1") -> dict:
    """Create a new Excel workbook from a list of rows (each row is a list of cell values)."""
    def _run():
        from openpyxl import Workbook
        p = _resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name
        for row in rows:
            ws.append(row)
        wb.save(str(p))
        return {"created": str(p), "rows": len(rows)}
    return await asyncio.to_thread(_run)


@mcp.tool()
async def xlsx_update_cell(path: str, cell: str, value, sheet: str | None = None) -> dict:
    """Update one cell's value, e.g. cell='B2'. Note: this drops formulas/formatting in re-saved cells."""
    def _run():
        from openpyxl import load_workbook
        p = _resolve(path)
        wb = load_workbook(str(p))
        ws = wb[sheet] if sheet else wb.active
        ws[cell] = value
        wb.save(str(p))
        return {"updated_cell": cell, "value": value}
    return await asyncio.to_thread(_run)


@mcp.tool()
async def xlsx_append_row(path: str, row: list, sheet: str | None = None) -> dict:
    """Append a row to an existing Excel sheet."""
    def _run():
        from openpyxl import load_workbook
        p = _resolve(path)
        wb = load_workbook(str(p))
        ws = wb[sheet] if sheet else wb.active
        ws.append(row)
        wb.save(str(p))
        return {"appended_to": str(p)}
    return await asyncio.to_thread(_run)


# --- PowerPoint (.pptx) ----------------------------------------------------

@mcp.tool()
async def pptx_read(path: str) -> list:
    """Read text content from every slide in a PowerPoint deck."""
    def _run():
        from pptx import Presentation
        prs = Presentation(str(_resolve(path)))
        slides = []
        for i, slide in enumerate(prs.slides, start=1):
            texts = [shape.text for shape in slide.shapes if shape.has_text_frame]
            slides.append({"slide": i, "text": "\n".join(texts)})
        return slides
    return await asyncio.to_thread(_run)


@mcp.tool()
async def pptx_create(path: str, slides: list[dict]) -> dict:
    """Create a new deck. Each slide dict: {"title": "...", "body": "..."}."""
    def _run():
        from pptx import Presentation
        p = _resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        prs = Presentation()
        layout = prs.slide_layouts[1]  # title + content
        for s in slides:
            slide = prs.slides.add_slide(layout)
            slide.shapes.title.text = s.get("title", "")
            if len(slide.placeholders) > 1:
                slide.placeholders[1].text = s.get("body", "")
        prs.save(str(p))
        return {"created": str(p), "slides": len(slides)}
    return await asyncio.to_thread(_run)


@mcp.tool()
async def pptx_add_slide(path: str, title: str, body: str = "") -> dict:
    """Add one slide to an existing deck."""
    def _run():
        from pptx import Presentation
        p = _resolve(path)
        prs = Presentation(str(p))
        layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(layout)
        slide.shapes.title.text = title
        if len(slide.placeholders) > 1:
            slide.placeholders[1].text = body
        prs.save(str(p))
        return {"added_to": str(p), "slide_count": sum(1 for _ in prs.slides)}
    return await asyncio.to_thread(_run)


# --- Smoke test / entry point --------------------------------------------

async def _smoke_test():
    print(f"Registered {len(mcp._tool_manager._tools)} operations:")
    for name in mcp._tool_manager._tools:
        print(f"  - {name}")
    print()
    print(f"FILES_ROOT_DIR: {FILES_ROOT_DIR or '(not set — absolute paths required)'}")
    print("\nTo serve:\n  python files.py --serve\n  python files.py --serve --transport http --port 8008")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8008)
    args = parser.parse_args()
    if not args.serve:
        asyncio.run(_smoke_test())
        return
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        print(f"Serving at http://{args.host}:{args.port}/mcp")
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
