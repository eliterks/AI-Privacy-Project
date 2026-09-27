from __future__ import annotations

import argparse
import html
import re
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
PAGE_WIDTH, PAGE_HEIGHT = A4

DOCUMENTS = (
    (
        ROOT / "docs" / "STUDENT_BUILD_ROADMAP.md",
        "AI-Security-Gateway-Student-Build-Roadmap.pdf",
        "Student Build Roadmap",
        "A guided path from v0.1 model development to a verifiable public v0.2 release",
    ),
    (
        ROOT / "docs" / "CURRENT_IMPLEMENTATION_STATUS.md",
        "AI-Security-Gateway-Current-Implementation-Status.pdf",
        "Current Implementation Status",
        "Built components, verification evidence, release blockers, and definition of done",
    ),
)

NAVY = colors.HexColor("#071D28")
DEEP_TEAL = colors.HexColor("#0B5962")
TEAL = colors.HexColor("#3BB8AE")
PALE_TEAL = colors.HexColor("#EAF4F4")
INK = colors.HexColor("#17242B")
MUTED = colors.HexColor("#667780")
GRID = colors.HexColor("#C9D9DC")
CODE_BG = colors.HexColor("#102A35")
CODE_FG = colors.HexColor("#EDF8F8")


def inline_markup(text: str) -> str:
    """Convert the small inline Markdown subset used in the source files."""
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"`([^`]+)`", r'<font name="Courier" color="#15505B">\1</font>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"\[([^]]+)]\((https?://[^)]+)\)", r'<a href="\2" color="#087B78">\1</a>', escaped)
    return escaped


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.25,
            leading=13.8,
            textColor=INK,
            spaceAfter=6,
        ),
        "h1": ParagraphStyle(
            "Heading1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            textColor=colors.HexColor("#0B3C49"),
            spaceBefore=0,
            spaceAfter=14,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14.5,
            leading=18,
            textColor=colors.HexColor("#0B3C49"),
            spaceBefore=15,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "Heading3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11.4,
            leading=14,
            textColor=colors.HexColor("#176370"),
            spaceBefore=11,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "h4": ParagraphStyle(
            "Heading4",
            parent=base["Heading4"],
            fontName="Helvetica-Bold",
            fontSize=9.8,
            leading=12,
            textColor=colors.HexColor("#285865"),
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.1,
            leading=13.2,
            leftIndent=13,
            firstLineIndent=-8,
            bulletIndent=2,
            textColor=INK,
            spaceAfter=3.5,
        ),
        "number": ParagraphStyle(
            "Number",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.1,
            leading=13.2,
            leftIndent=16,
            firstLineIndent=-12,
            bulletIndent=0,
            textColor=INK,
            spaceAfter=3.5,
        ),
        "label": ParagraphStyle(
            "Label",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.2,
            leading=12,
            textColor=colors.HexColor("#0B3C49"),
            spaceBefore=6,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "table": ParagraphStyle(
            "TableCell",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.35,
            leading=10.2,
            textColor=INK,
            spaceAfter=0,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.25,
            leading=9.6,
            textColor=colors.white,
            spaceAfter=0,
        ),
        "code": ParagraphStyle(
            "Code",
            fontName="Courier",
            fontSize=7.2,
            leading=10.2,
            leftIndent=8,
            rightIndent=8,
            textColor=CODE_FG,
            backColor=CODE_BG,
            borderColor=TEAL,
            borderWidth=0,
            borderPadding=8,
            spaceBefore=4,
            spaceAfter=9,
        ),
    }


STYLES = build_styles()


class DocumentationTemplate(BaseDocTemplate):
    def __init__(self, filename: Path, title: str, subtitle: str):
        self.document_title = title
        self.document_subtitle = subtitle
        self.generated = date.today().strftime("%d %B %Y")
        super().__init__(
            str(filename),
            pagesize=A4,
            leftMargin=17 * mm,
            rightMargin=17 * mm,
            topMargin=19 * mm,
            bottomMargin=19 * mm,
            title=title,
            author="AI Privacy Project",
            subject=subtitle,
        )
        cover_frame = Frame(0, 0, PAGE_WIDTH, PAGE_HEIGHT, id="cover", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        body_frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="body",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(
            (
                PageTemplate(id="cover", frames=(cover_frame,), onPage=self.draw_cover),
                PageTemplate(id="body", frames=(body_frame,), onPage=self.draw_body_chrome),
            )
        )

    def draw_cover(self, canvas, _doc) -> None:
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#0B3944"))
        canvas.circle(PAGE_WIDTH + 5 * mm, PAGE_HEIGHT - 35 * mm, 70 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#0B5056"))
        canvas.circle(PAGE_WIDTH - 5 * mm, -5 * mm, 62 * mm, fill=1, stroke=0)

        left = 27 * mm
        canvas.setFillColor(colors.HexColor("#62D7CF"))
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(left, PAGE_HEIGHT - 33 * mm, "AI SECURITY GATEWAY / V0.2 DOCUMENTATION")

        y = PAGE_HEIGHT - 80 * mm
        words = self.document_title.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if stringWidth(candidate, "Helvetica-Bold", 31) <= 145 * mm:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 31)
        for line in lines:
            canvas.drawString(left, y, line)
            y -= 12 * mm

        canvas.setFillColor(colors.HexColor("#62D7CF"))
        canvas.rect(left, y - 1 * mm, 28 * mm, 1.2 * mm, fill=1, stroke=0)
        y -= 12 * mm

        subtitle = Paragraph(
            html.escape(self.document_subtitle),
            ParagraphStyle("cover-subtitle", fontName="Helvetica", fontSize=13, leading=19, textColor=colors.HexColor("#D6E8EA")),
        )
        subtitle.wrapOn(canvas, 145 * mm, 35 * mm)
        subtitle.drawOn(canvas, left, y - 25 * mm)

        canvas.setFillColor(colors.HexColor("#ACC7CA"))
        canvas.setFont("Helvetica", 8.5)
        canvas.drawString(left, 35 * mm, "PROJECT: ELITERKS / AI-PRIVACY-PROJECT")
        canvas.drawString(left, 29 * mm, f"GENERATED: {self.generated.upper()}")
        canvas.drawString(left, 23 * mm, "FORMAT: FINAL PDF EDITION")
        canvas.restoreState()

    def draw_body_chrome(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(GRID)
        canvas.setLineWidth(0.45)
        canvas.line(17 * mm, PAGE_HEIGHT - 13 * mm, PAGE_WIDTH - 17 * mm, PAGE_HEIGHT - 13 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica-Bold", 7.2)
        canvas.drawString(17 * mm, PAGE_HEIGHT - 10 * mm, "AI SECURITY GATEWAY")
        canvas.setFont("Helvetica", 7.2)
        canvas.drawRightString(PAGE_WIDTH - 17 * mm, PAGE_HEIGHT - 10 * mm, self.document_title.upper())

        canvas.setStrokeColor(GRID)
        canvas.line(17 * mm, 13 * mm, PAGE_WIDTH - 17 * mm, 13 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(17 * mm, 9 * mm, "ELITERKS / AI-PRIVACY-PROJECT")
        canvas.drawRightString(PAGE_WIDTH - 17 * mm, 9 * mm, f"PAGE {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable) -> None:
        if isinstance(flowable, Paragraph) and flowable.style.name in {"Heading1", "Heading2", "Heading3"}:
            level = {"Heading1": 0, "Heading2": 1, "Heading3": 2}[flowable.style.name]
            text = flowable.getPlainText()
            key = f"section-{self.page}-{abs(hash((text, self.page)))}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def table_widths(rows: list[list[str]], available: float) -> list[float]:
    columns = len(rows[0])
    maxima = [max(len(row[index]) if index < len(row) else 0 for row in rows) for index in range(columns)]
    weights = [max(12.0, min(48.0, value ** 0.75)) for value in maxima]
    total = sum(weights)
    return [available * weight / total for weight in weights]


def make_table(raw_rows: list[list[str]], available: float) -> Table:
    normalized = [row + [""] * (len(raw_rows[0]) - len(row)) for row in raw_rows]
    data = []
    for row_index, row in enumerate(normalized):
        style = STYLES["table_header"] if row_index == 0 else STYLES["table"]
        data.append([Paragraph(inline_markup(cell), style) for cell in row])
    table = Table(data, colWidths=table_widths(normalized, available), repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            (
                ("BACKGROUND", (0, 0), (-1, 0), DEEP_TEAL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.45, GRID),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), (colors.white, colors.HexColor("#F2F7F7"))),
            )
        )
    )
    return table


def markdown_flowables(source: str, available_width: float) -> list:
    lines = source.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    story: list = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 2.5))
            index += 1
            continue

        if stripped.startswith("```"):
            index += 1
            code_lines = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1
            code = Preformatted("\n".join(code_lines), STYLES["code"], maxLineLength=105)
            code_box = Table([[code]], colWidths=[available_width], hAlign="LEFT")
            code_box.setStyle(
                TableStyle(
                    (
                        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                        ("LINEBEFORE", (0, 0), (0, -1), 3, TEAL),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    )
                )
            )
            story.append(code_box)
            story.append(Spacer(1, 9))
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            level = len(heading.group(1))
            story.append(Paragraph(inline_markup(heading.group(2)), STYLES[f"h{level}"]))
            index += 1
            continue

        if stripped.startswith("|") and index + 1 < len(lines) and is_table_separator(lines[index + 1]):
            rows = [split_table_row(stripped)]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(split_table_row(lines[index]))
                index += 1
            story.append(Spacer(1, 3))
            story.append(make_table(rows, available_width))
            story.append(Spacer(1, 5))
            continue

        bullet = re.match(r"^\s*[-*]\s+(.+)$", line)
        numbered = re.match(r"^\s*(\d+)\.\s+(.+)$", line)
        if bullet:
            story.append(Paragraph(inline_markup(bullet.group(1)), STYLES["bullet"], bulletText="•"))
            index += 1
            continue
        if numbered:
            story.append(Paragraph(inline_markup(numbered.group(2)), STYLES["number"], bulletText=f"{numbered.group(1)}."))
            index += 1
            continue

        labels = {
            "**Teach**", "**Build**", "**Build in Kaggle**", "**Build locally**",
            "**Publish the model**", "**Publish the application**", "**Checkpoint**", "**Release gate**",
        }
        if stripped in labels:
            story.append(Paragraph(inline_markup(stripped), STYLES["label"]))
            index += 1
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index]
            candidate_stripped = candidate.strip()
            if not candidate_stripped:
                break
            if re.match(r"^(#{1,4})\s+", candidate_stripped) or candidate_stripped.startswith("```"):
                break
            if re.match(r"^\s*[-*]\s+", candidate) or re.match(r"^\s*\d+\.\s+", candidate):
                break
            if candidate_stripped.startswith("|") and index + 1 < len(lines) and is_table_separator(lines[index + 1]):
                break
            paragraph_lines.append(candidate_stripped)
            index += 1
        text = " ".join(paragraph_lines)
        paragraph = Paragraph(inline_markup(text), STYLES["body"])
        if text.startswith("**Status date:**"):
            banner = Table([[paragraph]], colWidths=[available_width])
            banner.setStyle(
                TableStyle(
                    (
                        ("BACKGROUND", (0, 0), (-1, -1), PALE_TEAL),
                        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#87C9C2")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    )
                )
            )
            story.append(banner)
        else:
            story.append(paragraph)

    return story


def build(source_path: Path, output_path: Path, title: str, subtitle: str) -> None:
    document = DocumentationTemplate(output_path, title, subtitle)
    story = [NextPageTemplate("body"), PageBreak(), Paragraph(html.escape(title), STYLES["h1"])]
    story.extend(markdown_flowables(source_path.read_text(encoding="utf-8"), document.width))
    document.build(story)
    print(f"Created {output_path.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the two project documentation PDFs.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for source_path, filename, title, subtitle in DOCUMENTS:
        build(source_path, args.output_dir / filename, title, subtitle)


if __name__ == "__main__":
    main()
