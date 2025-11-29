"""PDF generation functions for FDSL."""

import io
import json
from typing import Any


def _to_pdf(data: Any, title: str = None, format: str = "auto") -> bytes:
    """
    Minimal and extensible PDF generator.
    - Supports optional title
    - Supports format override: auto | json | text | table

    Args:
        data: Any input (string, dict, list)
        title: Optional title text
        format: Rendering mode

    Returns:
        PDF bytes
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
    except ImportError:
        raise ImportError("Install reportlab: pip install reportlab")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # --- Title ---
    if title:
        story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
        story.append(Spacer(1, 12))

    # Normalize data
    is_list = isinstance(data, list)
    is_dict = isinstance(data, dict)
    is_list_of_dicts = is_list and data and isinstance(data[0], dict)

    # --- Format auto-detection ---
    if format == "auto":
        if is_list_of_dicts:
            format = "table"
        elif is_dict:
            format = "json"
        elif is_list:
            format = "json"
        else:
            format = "text"

    # --- JSON mode ---
    if format == "json":
        text = json.dumps(data, indent=2)
        for line in text.split("\n"):
            story.append(Paragraph(line, styles["Code"]))
            story.append(Spacer(1, 4))

    # --- Text mode ---
    elif format == "text":
        text = str(data)
        for line in text.split("\n"):
            if line.strip():
                story.append(Paragraph(line, styles["Normal"]))
                story.append(Spacer(1, 6))

    # --- Table mode (list of dicts) ---
    elif format == "table":
        if not is_list_of_dicts:
            # fallback for bad input
            text = json.dumps(data, indent=2)
            for line in text.split("\n"):
                story.append(Paragraph(line, styles["Code"]))
            doc.build(story)
            return buffer.getvalue()

        headers = list(data[0].keys())
        rows = [headers] + [[str(item.get(h, "")) for h in headers] for item in data]

        table = Table(rows, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ]))

        story.append(table)

    # --- Build ---
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


DSL_PDF_FUNCS = {
    "toPdf": (_to_pdf, (1, 3)),  # Allow 1–3 arguments (data, title?, format?)
}
