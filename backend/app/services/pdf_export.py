"""MailGuard PDF security report generator.

Presentation-only redesign. The renderer keeps the existing Report Generation
page/API contract: ``build_case_pdf(case: dict) -> bytes`` is the only entry
point, the case dictionary layout is unchanged, and every displayed value is
read from the same case fields as before. No parsing, scoring, authentication,
URL, attachment, AI or hashing behaviour lives in this module.

Report structure (four pages, ten numbered sections):

  page 1  01 CASE OVERVIEW / 02 EMAIL INFORMATION / 03 AUTHENTICATION
  page 2  04 ORIGIN & ROUTE ANALYSIS (origin metadata, Received hop table,
          route visualisation, forensic timeline)
  page 3  05 SECURITY FINDINGS / 06 URL ANALYSIS / 07 ATTACHMENTS /
          08 AI-ANALYST EXPLANATION / 09 RECOMMENDED ACTION
  page 4  10 EVIDENCE & INTEGRITY RECORD

Risk Score Breakdown is intentionally excluded.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (CondPageBreak, Frame, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from app.core.security import escape_for_report


# --------------------------------------------------------------------------
# Design tokens
# --------------------------------------------------------------------------
# Ink / structure
NAVY = colors.HexColor("#0E1A2B")
NAVY_MID = colors.HexColor("#1D2C42")
INK = colors.HexColor("#16202E")
MUTED = colors.HexColor("#5B6B7F")
FAINT = colors.HexColor("#8494A6")
LINE = colors.HexColor("#D5DCE4")
GRID = colors.HexColor("#E4E9EF")
BOX = colors.HexColor("#C3CBD6")
ZEBRA = colors.HexColor("#F7F9FB")
PANEL = colors.HexColor("#F4F6F9")
WHITE = colors.white

# Section numbering is always the same ink; accents below identify features.
SECTION_NUM_INK = colors.HexColor("#33415A")

# Section identity accents (one accent per feature, never per box)
BLUE = colors.HexColor("#1D4ED8")
TEAL = colors.HexColor("#0F766E")
AMBER = colors.HexColor("#B45309")
RED = colors.HexColor("#B42318")
PURPLE = colors.HexColor("#6D28D9")
VIOLET = colors.HexColor("#5B21B6")
SLATE = colors.HexColor("#334155")

# Status semantics (used only where a status is being communicated)
GREEN = colors.HexColor("#067647")
GRAY = MUTED

RED_SOFT = colors.HexColor("#FCF3F2")
AMBER_SOFT = colors.HexColor("#FDF6EC")
GREEN_SOFT = colors.HexColor("#F0FBF4")
GRAY_SOFT = colors.HexColor("#F5F7FA")
NAVY_SOFT = colors.HexColor("#F2F4F8")

# Legacy aliases kept so any other import of this module keeps resolving.
CYAN = TEAL
ORANGE = AMBER
LIGHT = PANEL
LIGHT_BLUE = NAVY_SOFT
LIGHT_PURPLE = colors.HexColor("#F5F3FC")

# Typography
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
MONO = "Courier"
MONO_BOLD = "Courier-Bold"

# Document grid
PAGE_W, PAGE_H = A4
MARGIN_L = 16 * mm
MARGIN_R = 16 * mm
MARGIN_T = 26 * mm
MARGIN_B = 20 * mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R          # 178 mm
LABEL_W = 40 * mm
GAP_SECTION = 6.2 * mm
GAP_BLOCK = 3.6 * mm
GAP_ROUTE = 5.4 * mm
GAP_TIGHT = 1.8 * mm


def _frame_padding():
    """reportlab's Frame wraps its content in a small padding; the document
    margins are offset by exactly this amount so that every rule, column edge
    and running head/foot line lands on the declared grid."""
    try:
        return float(Frame(0, 0, 10, 10)._leftPadding)
    except Exception:                                    # pragma: no cover
        return 6.0


FRAME_PAD = _frame_padding()

DASH = "—"


def esc(value: Any) -> str:
    return "" if value is None else escape_for_report(str(value))


def _mk_style(name, base=None, **kw):
    """Create/register a ParagraphStyle, tolerating older reportlab versions
    that do not accept character-tracking as a style attribute."""
    try:
        return ParagraphStyle(name, parent=base, **kw)
    except (TypeError, ValueError):
        kw.pop("tracking", None)
        return ParagraphStyle(name, parent=base, **kw)


def styles():
    s = getSampleStyleSheet()

    # Masthead
    s.add(_mk_style("ReportKicker", fontName=FONT_BOLD, fontSize=6.4, leading=8, textColor=NAVY))
    s.add(_mk_style("ReportTitle", fontName=FONT_BOLD, fontSize=20, leading=22.5,
                    textColor=NAVY))
    s.add(_mk_style("ReportSubtitle", fontName=FONT, fontSize=8.4, leading=11, textColor=MUTED))

    # Section furniture
    # Section numbering: identical shape, weight and colour in every section.
    # The per-section accent appears only in the hairline under the heading.
    s.add(_mk_style("SectionNumber", fontName=MONO_BOLD, fontSize=10.2, leading=13,
                    textColor=SECTION_NUM_INK))
    s.add(_mk_style("Section", fontName=FONT_BOLD, fontSize=12.2, leading=14.5, textColor=NAVY))
    s.add(_mk_style("SectionMeta", fontName=MONO_BOLD, fontSize=6.4, leading=8,
                    textColor=FAINT, alignment=TA_RIGHT))
    s.add(_mk_style("SubHead", fontName=FONT_BOLD, fontSize=8.0, leading=10, textColor=NAVY_MID))
    s.add(_mk_style("SubHeadNote", fontName=FONT, fontSize=6.6, leading=9,
                    textColor=FAINT, alignment=TA_RIGHT))

    # Text
    s.add(_mk_style("Label", fontName=FONT_BOLD, fontSize=6.6, leading=8.6, textColor=MUTED))
    s.add(_mk_style("Value", fontName=FONT, fontSize=8.4, leading=11, textColor=INK))
    s.add(_mk_style("ValueStrong", fontName=FONT_BOLD, fontSize=8.4, leading=11,
                    textColor=INK))
    s.add(_mk_style("Body", fontName=FONT, fontSize=8.8, leading=12.2, textColor=INK))
    s.add(_mk_style("Small", fontName=FONT, fontSize=7.0, leading=9.6, textColor=MUTED))
    s.add(_mk_style("Caption", fontName=FONT, fontSize=6.5, leading=8.8, textColor=FAINT))

    # Tables
    s.add(_mk_style("TH", fontName=FONT_BOLD, fontSize=6.6, leading=8.4, textColor=WHITE))
    s.add(_mk_style("TB", fontName=FONT, fontSize=7.7, leading=10.0, textColor=INK))
    s.add(_mk_style("TBStrong", fontName=FONT_BOLD, fontSize=7.7, leading=10.0,
                    textColor=INK))
    s.add(_mk_style("TBNumeric", fontName=MONO_BOLD, fontSize=7.4, leading=10.0,
                    textColor=NAVY, alignment=TA_CENTER))

    # Technical evidence (monospaced, wraps predictably)
    s.add(_mk_style("Mono", fontName=MONO, fontSize=6.9, leading=9.2, textColor=INK))
    s.add(_mk_style("MonoStrong", fontName=MONO_BOLD, fontSize=6.9, leading=9.2,
                    textColor=INK))
    s.add(_mk_style("MonoSmall", fontName=MONO, fontSize=6.3, leading=8.4, textColor=INK))

    s.add(_mk_style("Center", fontName=FONT, fontSize=7.0, leading=9,
                    textColor=MUTED, alignment=TA_CENTER))
    s.add(_mk_style("Status", fontName=FONT_BOLD, fontSize=6.4, leading=8,
                    alignment=TA_CENTER))
    s.add(_mk_style("RiskValue", fontName=FONT_BOLD, fontSize=21, leading=23.5,
                    textColor=NAVY))
    s.add(_mk_style("BandRow", fontName=FONT_BOLD, fontSize=6.8, leading=9.4, textColor=NAVY))
    s.add(_mk_style("BandRange", fontName=MONO, fontSize=6.6, leading=9.4, textColor=FAINT,
                    alignment=TA_RIGHT))
    s.add(_mk_style("StatValue", fontName=MONO_BOLD, fontSize=11, leading=13, textColor=NAVY))
    return s


# --------------------------------------------------------------------------
# Text helpers
# --------------------------------------------------------------------------
def P(value, s, style="Value"):
    """Escaped plain paragraph (no width-aware wrapping)."""
    return Paragraph(esc(value), s[style])


def _split_long(word, font, size, max_w):
    pieces, cur = [], ""
    for ch in word:
        if cur and pdfmetrics.stringWidth(cur + ch, font, size) > max_w:
            pieces.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        pieces.append(cur)
    return pieces or [word]


def _wrap_lines(text, font, size, max_w):
    """Width-aware manual line breaking: never overflows the column and never
    clips, for URLs / hashes / hostnames that contain no spaces."""
    if not text:
        return []
    units = []
    for w_index, word in enumerate(text.split()):
        parts = [word] if pdfmetrics.stringWidth(word, font, size) <= max_w \
            else _split_long(word, font, size, max_w)
        for p_index, piece in enumerate(parts):
            units.append((piece, w_index > 0 and p_index == 0))
    lines, cur = [], ""
    for piece, space_before in units:
        candidate = f"{cur} {piece}" if (space_before and cur) else f"{cur}{piece}"
        if not cur or pdfmetrics.stringWidth(candidate, font, size) <= max_w:
            cur = candidate
        else:
            lines.append(cur)
            cur = piece
    if cur:
        lines.append(cur)
    return lines


def wrapped(value, s, style, avail_w, mode="text"):
    """Escaped, pre-wrapped paragraph. ``mode='mono'`` uses the monospaced
    face and breaks long technical tokens at fixed glyph widths."""
    st = s[style]
    text = "" if value is None else str(value)
    font = MONO if mode == "mono" else st.fontName
    if mode == "mono":
        st = ParagraphStyle(f"{style}-mono", parent=st, fontName=MONO)
    lines = _wrap_lines(text, font, st.fontSize, max(20.0, avail_w))
    if not lines:
        return Paragraph(esc(DASH), st)
    return Paragraph("<br/>".join(esc(line) for line in lines), st)


def labelled(value):
    return value if value not in (None, "") else DASH


# --------------------------------------------------------------------------
# Reusable components
# --------------------------------------------------------------------------
def tone_of(value):
    """Map a stored verdict to one of the four status tones."""
    v = str(value or "").strip().lower()
    if v in {"high", "red", "fail", "softfail", "permerror", "temperror", "mismatch",
             "suspicious", "flagged", "block", "listed", "yes"}:
        return "red"
    if v in {"medium", "moderate", "yellow", "review", "neutral", "partial"}:
        return "amber"
    if v in {"low", "pass", "ok", "green", "match", "none", "no", "clean",
             "no flag", "not listed"}:
        return "green"
    return "gray"


TONES = {
    "red": (RED, RED_SOFT),
    "amber": (AMBER, AMBER_SOFT),
    "green": (GREEN, GREEN_SOFT),
    "gray": (GRAY, GRAY_SOFT),
    "navy": (NAVY, NAVY_SOFT),
}


def status_label(text, tone, s, width=None, align="center"):
    """Compact status chip: neutral fill, hairline border, coloured text.
    Colour carries the status; the chip itself never shouts."""
    fg, bg = TONES.get(tone, TONES["gray"])
    st = ParagraphStyle("chip", parent=s["Status"], textColor=fg,
                        alignment=TA_CENTER if align == "center" else TA_LEFT)
    p = Paragraph(esc(text), st)
    if width is None:
        width = max(pdfmetrics.stringWidth(str(text), FONT_BOLD, 6.4) + 14, 18 * mm)
    t = Table([[p]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.4, BOX),
        ("LINEBEFORE", (0, 0), (0, -1), 1.6, fg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
    ]))
    return t


def badge(text, fg, bg, s, width=30 * mm):
    """Kept for compatibility with the previous module surface: a coloured
    status chip. New code calls status_label() with a semantic tone."""
    st = ParagraphStyle("badge", parent=s["Status"], textColor=fg)
    p = Paragraph(esc(text), st)
    t = Table([[p]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.4, fg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
    ]))
    return t


def section_heading(number, title, s, color=BLUE, total=10):
    """Identical numbering treatment for all ten sections: an unboxed
    monospaced number, a caps title, a right-aligned position marker and a
    single hairline rule. Only the rule carries the section accent."""
    num_w, meta_w = 10.8 * mm, 26 * mm
    heading = Table([[Paragraph(esc(number), s["SectionNumber"]),
                      Paragraph(esc(title), s["Section"]),
                      Paragraph(f"SEC {esc(number)} / {total}", s["SectionMeta"])]],
                    colWidths=[num_w, CONTENT_W - num_w - meta_w, meta_w], hAlign="LEFT")
    heading.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.7, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 4.5),
        ("RIGHTPADDING", (1, 0), (1, 0), 6),
        ("RIGHTPADDING", (2, 0), (2, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.0),
    ]))
    return heading


def sub_head(title, s, note=None, width=CONTENT_W):
    cells = [Paragraph(esc(title), s["SubHead"])]
    note_w = 0
    if note:
        note_w = 52 * mm
        cells.append(Paragraph(esc(note), s["SubHeadNote"]))
        col_w = [width - note_w, note_w]
    else:
        col_w = [width]
    row = Table([cells], colWidths=col_w, hAlign="LEFT")
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.0),
    ]))
    return row


def forensic_table(rows, widths, s, zebra_start=2, valign="TOP", box=True,
                   vgrid=True, col_align=None, pad=3.4, lead=None):
    """The single table language used by every data table in the report."""
    t = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), valign),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("LINEBELOW", (0, 0), (-1, -2), 0.35, LINE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, NAVY),
    ]
    if box:
        cmds.append(("BOX", (0, 0), (-1, -1), 0.5, BOX))
    if vgrid:
        cmds.append(("LINEAFTER", (0, 1), (-2, -1), 0.35, GRID))
    for idx in range(zebra_start, len(rows), 2):
        cmds.append(("BACKGROUND", (0, idx), (-1, idx), ZEBRA))
    if col_align:
        for col, al in col_align.items():
            cmds.append(("ALIGN", (col, 0), (col, -1), al))
    t.setStyle(TableStyle(cmds))
    return t


def kv(rows, s, accent=None, label_w=LABEL_W, value_style="Value",
       mono_keys=None, width=CONTENT_W):
    """Label/value evidence grid: neutral labels, hairline rules, wrapped
    values. ``mono_keys`` renders those values in the monospaced face."""
    mono_keys = mono_keys or set()
    value_w = width - label_w - 20
    data, cmds = [], [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), PANEL),
        ("LINEBELOW", (0, 0), (-1, -2), 0.35, LINE),
        ("BOX", (0, 0), (-1, -1), 0.5, BOX),
        ("LINEAFTER", (0, 0), (0, -1), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.6),
    ]
    for i, row in enumerate(rows):
        key, value = row[0], row[1]
        mono = "mono" if (len(row) > 2 and row[2] == "mono") or key in mono_keys else "text"
        style = "Mono" if mono == "mono" else value_style
        data.append([P(key, s, "Label"),
                     wrapped(labelled(value), s, style, value_w, mode=mono)])
        if i % 2 == 1:
            cmds.append(("BACKGROUND", (1, i), (1, i), ZEBRA))
    t = Table(data, colWidths=[label_w, width - label_w], hAlign="LEFT")
    if accent is not None:
        cmds.append(("LINEBEFORE", (0, 0), (0, -1), 1.6, accent))
    t.setStyle(TableStyle(cmds))
    return t


def field_grid(rows, s, width=CONTENT_W, cols=2, mono_keys=None):
    """Compact label-over-value grid used for origin metadata."""
    mono_keys = mono_keys or set()
    cell_w = width / cols
    label_w = 24 * mm
    value_w = cell_w - label_w
    data, style_cmds = [], [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, BOX),
        ("LINEAFTER", (0, 0), (-3, -1), 0.35, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 3.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for col in range(0, 2 * cols, 2):
        style_cmds.append(("BACKGROUND", (col, 0), (col, -1), PANEL))
    for i in range(0, len(rows), cols):
        row_cells = []
        for j, (key, value) in enumerate(rows[i:i + cols]):
            mono = key in mono_keys
            style = "Mono" if mono else "Value"
            row_cells.extend([
                P(key, s, "Label"),
                wrapped(labelled(value), s, style, value_w - 12, mode="mono" if mono else "text"),
            ])
        data.append(row_cells)
    t = Table(data, colWidths=[label_w, value_w] * cols, hAlign="LEFT")
    for r in range(1, len(data)):
        style_cmds.append(("LINEBELOW", (0, r - 1), (-1, r - 1), 0.35, LINE))
    t.setStyle(TableStyle(style_cmds))
    return t


def note_block(title, body, s, tone="navy", width=CONTENT_W, note=None):
    """Bordered prose block (executive assessment, analyst narrative): a label
    band over the text inside one box. No decorative fills."""
    fg, _bg = TONES.get(tone, TONES["navy"])
    band_left = Paragraph(esc(title), s["SubHead"])
    band_right = Paragraph(esc(note or "REPORTED VERBATIM FROM STORED CASE DATA"), s["SubHeadNote"])
    text_w = width - 14 - 14 - 4
    tbl = Table([[band_left, band_right],
                 [wrapped(body, s, "Body", text_w), ""]],
                colWidths=[width * 0.48, width * 0.52], hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("SPAN", (0, 1), (1, 1)),
        ("BACKGROUND", (0, 0), (-1, 0), PANEL),
        ("BOX", (0, 0), (-1, -1), 0.5, BOX),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, LINE),
        ("LINEBEFORE", (0, 0), (0, 0), 1.7, fg),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("VALIGN", (0, 1), (-1, 1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 3.0),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3.0),
        ("TOPPADDING", (0, 1), (-1, 1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
    ]))
    return KeepTogether([tbl])


def severity_palette(value):
    v = str(value or "").lower()
    if v == "red":
        return RED, RED_SOFT, "HIGH RISK"
    if v == "yellow":
        return AMBER, AMBER_SOFT, "MEDIUM RISK"
    if v == "green":
        return GREEN, GREEN_SOFT, "LOW RISK"
    try:
        score = float(value)
    except (TypeError, ValueError):
        return MUTED, LIGHT, "UNKNOWN RISK"
    if score >= 70:
        return RED, RED_SOFT, "HIGH RISK"
    if score >= 35:
        return AMBER, AMBER_SOFT, "MEDIUM RISK"
    return GREEN, GREEN_SOFT, "LOW RISK"


def auth_badge(value, s):
    v = str(value or "none").lower()
    if v == "pass":
        return status_label("PASS", "green", s, 30 * mm)
    if v in {"fail", "softfail", "permerror", "temperror", "mismatch"}:
        return status_label(v.upper(), "red", s, 30 * mm)
    if v == "match":
        return status_label("MATCH", "green", s, 30 * mm)
    if v in {"neutral", "none"}:
        return status_label("NOT PRESENT" if v == "none" else v.upper(), "gray", s, 30 * mm)
    return status_label(v.upper(), tone_of(v), s, 30 * mm)


def format_date(value):
    if not value:
        return ""
    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        ).strftime("%d %b %Y %H:%M UTC")
    except ValueError:
        return str(value)


def collect_findings(case, trace):
    out = []

    # Primary scoring findings are stored in dashboard.findings by the
    # current /api/analyze response shape.
    dashboard_findings = ((case.get("dashboard") or {}).get("findings") or [])
    analysis_findings = ((case.get("analysis") or {}).get("findings") or [])
    source_findings = dashboard_findings or analysis_findings

    for item in source_findings:
        if isinstance(item, dict):
            out.append({
                "severity": str(item.get("severity") or "low").upper(),
                "signal": item.get("signal") or item.get("category") or "Security finding",
                "message": item.get("message") or item.get("detail") or "",
            })

    checks = case.get("headerChecks") or {}
    if checks.get("senderDomainMismatch"):
        out.append({
            "severity": "HIGH",
            "signal": "Reply-To mismatch",
            "message": "The Reply-To domain differs from the sender domain.",
        })

    for hop in trace.get("hops") or []:
        for flag in hop.get("suspicious_flags") or []:
            if not isinstance(flag, dict):
                continue
            reason = str(flag.get("reason") or "origin signal")
            out.append({
                "severity": "HIGH" if reason == "blacklist" else "MEDIUM",
                "signal": reason.replace("_", " ").title(),
                "message": flag.get("detail") or reason,
            })

    seen = set()
    unique = []
    for item in out:
        key = (item["severity"], item["signal"], item["message"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


# --------------------------------------------------------------------------
# Section renderers (presentation only)
# --------------------------------------------------------------------------
def render_findings(findings, s, width=CONTENT_W):
    """Forensic evidence table: status colour is confined to SEVERITY."""
    if not findings:
        return kv([("Status", "No explicit security findings were recorded.")], s, GREEN)

    widths = [27 * mm, 46 * mm, width - 73 * mm]
    rows = [[Paragraph("SEVERITY", s["TH"]), Paragraph("SIGNAL", s["TH"]),
             Paragraph("EVIDENCE", s["TH"])]]
    for f in findings:
        sev = str(f["severity"]).upper()
        rows.append([
            status_label(sev, tone_of(sev), s, widths[0] - 10),
            wrapped(f["signal"], s, "TBStrong", widths[1] - 10),
            wrapped(f["message"], s, "TB", widths[2] - 10),
        ])
    return forensic_table(rows, widths, s, valign="MIDDLE")


def render_hops(hops, s, width=CONTENT_W):
    widths = [12 * mm, 46 * mm, 32 * mm, width - 12 * mm - 46 * mm - 32 * mm - 27 * mm, 27 * mm]
    rows = [[Paragraph("HOP", s["TH"]), Paragraph("IP / HOST", s["TH"]),
             Paragraph("LOCATION", s["TH"]), Paragraph("ISP / ASN", s["TH"]),
             Paragraph("STATUS", s["TH"])]]
    for i, hop in enumerate(hops, 1):
        flagged = bool(
            hop.get("flagged")
            or hop.get("suspicious_flags")
            or (hop.get("blacklist") or {}).get("listed")
        )
        tone, status = (
            ("red", "FLAGGED") if flagged
            else ("gray", "INTERNAL") if hop.get("internal")
            else ("green", "OK")
        )
        host = hop.get("reverse") or hop.get("hostname") or ""
        loc = hop.get("city") or ""
        if hop.get("country"):
            loc = f"{loc} / {hop['country']}" if loc else str(hop["country"])
        ip_txt = hop.get("ip") or "Internal"
        ip_host = [wrapped(ip_txt, s, "MonoStrong", widths[1] - 10, mode="mono")]
        if host:
            ip_host.append(Paragraph(
                f'<font size="6.5" color="{MUTED.hexval()}">{esc(host)}</font>', s["TB"]))
        else:
            ip_host.append(Paragraph(f'<font size="6.5" color="{FAINT.hexval()}">{esc(DASH)}</font>', s["TB"]))
        rows.append([
            Paragraph(esc(f"{i:02d}"), s["TBNumeric"]),
            ip_host,
            wrapped(labelled(loc), s, "TB", widths[2] - 10),
            [
                wrapped(labelled(hop.get("isp")), s, "TB", widths[3] - 10),
                Paragraph(f'<font size="6.5" color="{MUTED.hexval()}">ASN '
                          f'{esc(labelled(hop.get("asn")))}</font>', s["TB"]),
            ],
            status_label(status, tone, s, widths[4] - 10),
        ])
    return forensic_table(rows, widths, s, pad=6.4, valign="MIDDLE")


def render_trace(hops, s, width=CONTENT_W):
    """Compact route ribbon: kept deliberately small, the hop table above it
    carries the detail."""
    public = [h for h in hops if h.get("ip")]
    if len(public) < 2:
        return kv([("Trace route", "Insufficient geolocated public hops for a route diagram.")],
                  s, GRAY)

    n = len(public)
    arrow_w = 5.4 * mm
    box_w = (width - arrow_w * (n - 1)) / n
    cells, col_w = [], []
    for idx, hop in enumerate(public):
        flagged = bool(
            hop.get("flagged")
            or hop.get("suspicious_flags")
            or (hop.get("blacklist") or {}).get("listed")
        )
        internal = bool(hop.get("internal"))
        tone = "red" if flagged else ("gray" if internal else "navy")
        fg = TONES[tone][0]
        label = hop.get("city") or hop.get("country") or ("internal relay" if internal else "Unknown")
        node = Table([[Paragraph(
            f'<font size="7" color="{fg.hexval()}"><b>{esc(hop.get("ip"))}</b></font><br/>'
            f'<font size="6.2" color="{MUTED.hexval()}">{esc(label)}</font>',
            ParagraphStyle("node", parent=s["Center"], leading=8.8),
        )]], colWidths=[box_w])
        node.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, BOX),
            ("LINEABOVE", (0, 0), (-1, 0), 1.6, fg),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("TOPPADDING", (0, 0), (-1, -1), 3.2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        cells.append(node)
        col_w.append(box_w)
        if idx < n - 1:
            cells.append(Paragraph(f'<font size="7.5" color="{FAINT.hexval()}">&#8250;</font>',
                                   s["Center"]))
            col_w.append(arrow_w)
    ribbon = Table([cells], colWidths=col_w, hAlign="LEFT")
    ribbon.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    legend = Paragraph(
        f'<font color="{RED.hexval()}"><b>\u2022</b></font> flagged hop&nbsp;&nbsp;&nbsp;'
        f'<font color="{NAVY.hexval()}"><b>\u2022</b></font> unremarkable hop&nbsp;&nbsp;&nbsp;'
        f'<font color="{GRAY.hexval()}"><b>\u2022</b></font> internal relay&nbsp;&nbsp;&nbsp;'
        f'<font color="{MUTED.hexval()}">Order follows the stored Received chain.</font>',
        s["Caption"],
    )
    return KeepTogether([ribbon, Spacer(1, 1.2 * mm), legend])


def _route_notes(hops, first_public):
    """One-line route summary derived from the stored hop list (no new data)."""
    flagged = [h for h in hops if h.get("flagged") or h.get("suspicious_flags")
               or (h.get("blacklist") or {}).get("listed")]
    internal = [h for h in hops if h.get("internal")]
    txt = (f"{len(hops)} Received hop(s) recorded  \u00b7  {len(flagged)} carrying origin flags  "
           f"\u00b7  {len(internal)} internal relay(s)  \u00b7  first public hop ")
    if first_public:
        place = first_public.get("city") or first_public.get("country")
        txt += f"{first_public.get('ip')}" + (f" ({place})" if place else "")
    else:
        txt += "not identified"
    return txt


def render_timeline(hops, metadata, analyzed_at, s, width=CONTENT_W):
    """Forensic timeline assembled only from timestamps already stored on the
    case: the message header date, each Received hop, and the analysis record."""
    events = []
    if metadata.get("date"):
        events.append(("Header date", "Message Date header", str(metadata["date"]), DASH))
    for i, hop in enumerate(hops or [], 1):
        stamp = hop.get("timestamp") or hop.get("date")
        if not stamp:
            continue
        where = hop.get("ip") or hop.get("hostname") or hop.get("reverse") or "internal relay"
        place = hop.get("city") or DASH
        if hop.get("country"):
            place = f"{place} / {hop['country']}" if hop.get("city") else str(hop["country"])
        events.append((f"Hop {i:02d}", str(where), str(stamp), place))
    if analyzed_at:
        events.append(("Case record", "MailGuard analysis entry", str(analyzed_at), DASH))

    if len(events) < 2:
        return kv([("Timeline", "Per-hop timestamps are not stored with this case, "
                                "so no forensic timeline can be reconstructed.")], s, GRAY)

    widths = [24 * mm, 50 * mm, 40 * mm, width - 114 * mm]
    rows = [[Paragraph("EVENT", s["TH"]), Paragraph("SOURCE", s["TH"]),
             Paragraph("LOCATION", s["TH"]), Paragraph("TIMESTAMP (UTC)", s["TH"])]]
    for label, source, stamp, place in events:
        rows.append([
            P(label, s, "TBStrong"),
            wrapped(source, s, "Mono", widths[1] - 10, mode="mono"),
            wrapped(place or DASH, s, "TB", widths[2] - 10),
            wrapped(format_date(stamp) or stamp, s, "Mono", widths[3] - 10, mode="mono"),
        ])
    return forensic_table(rows, widths, s, valign="MIDDLE", pad=5.4)


def render_urls(urls, dashboard, s, width=CONTENT_W):
    suspicious = int(((dashboard.get("metrics") or {}).get("suspiciousUrlCount") or 0))
    if not urls:
        return kv([("Extracted URLs", "None detected.")], s, TEAL)

    widths = [9 * mm, width - 9 * mm - 30 * mm - 44 * mm, 30 * mm, 44 * mm]
    rows = [[Paragraph("#", s["TH"]), Paragraph("URL", s["TH"]),
             Paragraph("STATUS", s["TH"]), Paragraph("ANALYSIS RESULT", s["TH"])]]
    for i, raw in enumerate(urls, 1):
        if isinstance(raw, dict):
            url = raw.get("url") or raw.get("value") or ""
            is_suspicious = bool(raw.get("suspicious"))
            reason = raw.get("reason") or raw.get("verdict") or ""
        else:
            url = str(raw)
            is_suspicious = i <= suspicious
            reason = ""
        if is_suspicious:
            tone, status = "red", "SUSPICIOUS"
            result = reason or "Flagged by the stored case analysis."
        else:
            tone, status = "green", "EXTRACTED"
            result = reason or ("Extracted from the email; no per-URL reputation result "
                               "is stored in this case.")
        rows.append([
            Paragraph(esc(f"{i:02d}"), s["TBNumeric"]),
            wrapped(url, s, "Mono", widths[1] - 10, mode="mono"),
            status_label(status, tone, s, widths[2] - 10),
            wrapped(result, s, "TB", widths[3] - 10),
        ])
    t = forensic_table(rows, widths, s)
    return t


def render_attachments(items, s, width=CONTENT_W):
    if not items:
        return kv([("Attachments", "None detected.")], s, PURPLE)

    widths = [50 * mm, 32 * mm, 27 * mm, width - 109 * mm]
    rows = [[Paragraph("FILE", s["TH"]), Paragraph("TYPE / SIZE", s["TH"]),
             Paragraph("STATUS", s["TH"]), Paragraph("PARSER RESULT", s["TH"])]]
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("filename") or "Unnamed attachment"
        ext = item.get("extension") or DASH
        size = item.get("size")
        suspicious = bool(item.get("suspicious"))
        reason = item.get("reason") or (
            "Flagged by the parser." if suspicious else "No parser-level issue recorded."
        )
        rows.append([
            wrapped(name, s, "MonoStrong", widths[0] - 10, mode="mono"),
            [Paragraph(f'<font size="6.5" color="{MUTED.hexval()}"><b>EXT</b></font>  '
                       f'{esc(ext)}', s["Mono"]),
             Paragraph(f'<font size="6.5" color="{MUTED.hexval()}"><b>SIZE</b></font>  '
                       f'{esc(str(size) if size is not None else DASH)} bytes', s["Mono"])],
            status_label("SUSPICIOUS" if suspicious else "NO FLAG",
                         "red" if suspicious else "green", s, widths[2] - 10),
            wrapped(reason, s, "TB", widths[3] - 10),
        ])
    return forensic_table(rows, widths, s)


def _action_tone(action):
    """Status colour for the disposition line only (never the whole block)."""
    text = str(action or "").upper()
    if text.startswith("BLOCK"):
        return "red"
    if "QUARANTINE" in text:
        return "amber"
    if "RELEASE" in text or text.startswith("ALLOW"):
        return "green"
    return "gray"


def recommendation(score, findings):
    try:
        value = float(score)
    except (TypeError, ValueError):
        value = 0
    high = sum(1 for f in findings if str(f.get("severity")).upper() == "HIGH")
    if value >= 70 or high >= 2:
        return "BLOCK / QUARANTINE", RED, RED_SOFT, "Treat this message as high risk. Do not open links or attachments."
    if value >= 35 or high == 1:
        return "REVIEW / QUARANTINE", AMBER, AMBER_SOFT, "Review the evidence before delivery and validate sender, origin, and URLs."
    return "REVIEW / RELEASE", GREEN, GREEN_SOFT, "No strong blocking signal is present in the stored case data."


# --------------------------------------------------------------------------
# Page furniture
# --------------------------------------------------------------------------
def draw_header_footer(canvas, document):
    """Running head / foot: hairline structure only, no decorative blocks."""
    meta = getattr(document, "_mailguard_meta", None) or {}
    canvas.saveState()
    w, h = A4

    # running head: single measured line, left descriptor + right hand marker
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(1.1)
    canvas.line(MARGIN_L, h - 18 * mm, w - MARGIN_R, h - 18 * mm)
    right_txt = "CONFIDENTIAL"
    case_id = meta.get("case_id")
    if case_id:
        right_txt = f"CONFIDENTIAL  \u00b7  CASE {case_id}"
    left_txt = "MailGuard  \u2014  Digital Forensics / SOC Incident Response / Email Threat Analysis"
    canvas.setFont(FONT_BOLD, 7.4)
    left_w = pdfmetrics.stringWidth(left_txt, FONT_BOLD, 7.4) + 6
    right_w = pdfmetrics.stringWidth(right_txt, MONO, 6.4)
    avail = (w - MARGIN_R) - MARGIN_L
    if left_w + right_w > avail:
        left_txt = "MailGuard  \u2014  Digital Forensics / SOC Incident Response"
    canvas.setFillColor(NAVY)
    canvas.setFont(FONT_BOLD, 7.4)
    canvas.drawString(MARGIN_L, h - 15.2 * mm, left_txt)
    canvas.setFont(MONO, 6.4)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(w - MARGIN_R, h - 15.2 * mm, esc(right_txt))

    # running foot
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.45)
    canvas.line(MARGIN_L, 13.6 * mm, w - MARGIN_R, 13.6 * mm)
    canvas.setFont(FONT, 6.2)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN_L, 9.6 * mm, "MailGuard Security Analysis Report")
    total = meta.get("page_total")
    label = f"Page {document.page} of {total}" if total else f"Page {document.page}"
    canvas.drawCentredString(w / 2.0, 9.6 * mm, "Generated from the stored case record")
    canvas.setFont(MONO, 6.2)
    canvas.drawRightString(w - MARGIN_R, 9.6 * mm, label)
    canvas.restoreState()


# --------------------------------------------------------------------------
# Report assembly
# --------------------------------------------------------------------------
def _risk_block(score, verdict, fg, findings, urls, attachments, s):
    """Formal classification block: score, classification, evidence volume and
    the severity band the stored score falls into. Structure over decoration."""
    bands = [("HIGH", "70 - 100", lambda v: v >= 70),
             ("MEDIUM", "35 - 69", lambda v: 35 <= v < 70),
             ("LOW", "0 - 34", lambda v: v < 35)]
    try:
        value = float(score)
    except (TypeError, ValueError):
        value = None
    band_rows, band_cmds = [], []
    for idx, (name, rng, pred) in enumerate(bands):
        active = value is not None and bool(pred(value))
        colour = fg if active else FAINT
        band_rows.append([
            Paragraph(f'<font color="{colour.hexval()}" size="6.8"><b>{name}</b></font>', s["TB"]),
            Paragraph(f'<font color="{FAINT.hexval()}" size="6.6">{rng}</font>',
                      ParagraphStyle("bandr", parent=s["TB"], alignment=TA_RIGHT)),
        ])
        if active:
            band_cmds.append(("LINEBEFORE", (0, idx), (0, idx), 1.7, fg))
            band_cmds.append(("BACKGROUND", (0, idx), (-1, idx), TONES[tone_of(name)][1]))
    band_w = CONTENT_W - 124 * mm - 14
    band = Table(band_rows, colWidths=[band_w - 26 * mm, 26 * mm], hAlign="LEFT")
    band.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
    ] + band_cmds))

    counts = []
    for name, value_ in (("FINDINGS", len(findings)), ("URLS", len(urls)),
                         ("ATTACHMENTS", len(attachments))):
        counts.append([Paragraph(esc(name), s["Label"]),
                       Paragraph(esc(value_), s["StatValue"])])
    counts_tbl = Table([[c[0] for c in counts], [c[1] for c in counts]],
                       colWidths=[17 * mm, 14 * mm, 27 * mm], hAlign="LEFT")
    counts_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("LINEBEFORE", (1, 0), (-1, -1), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 0.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
    ]))

    score_cell = [
        Paragraph("RISK SCORE", s["Label"]),
        Spacer(1, 1.4 * mm),
        Paragraph(f'<font color="{fg.hexval()}" size="21"><b>{esc(score)}</b></font>'
                  f'<font color="{MUTED.hexval()}" size="8"> / 100</font>', s["RiskValue"]),
        Spacer(1, 1.0 * mm),
        Paragraph("ASSIGNED BY THE RISK SCORING MODEL", s["Caption"]),
    ]
    class_cell = [
        Paragraph("CLASSIFICATION", s["Label"]),
        Spacer(1, 1.4 * mm),
        status_label(verdict, tone_of(verdict), s, 42 * mm, align="left"),
        Spacer(1, 3.2 * mm),
        counts_tbl,
    ]
    band_cell = [
        Paragraph("SEVERITY BAND", s["Label"]),
        Spacer(1, 1.4 * mm),
        band,
    ]
    widths = [56 * mm, 68 * mm, CONTENT_W - 124 * mm]
    block = Table([[score_cell, class_cell, band_cell]], colWidths=widths, hAlign="LEFT")
    block.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.5, BOX),
        ("LINEBELOW", (0, 0), (-1, -1), 1.7, fg),
        ("LINEAFTER", (0, 0), (1, 0), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7.5),
    ]))
    return block


def _masthead(case_id, analyzed_at, verdict, fg, s):
    ident_rows = [
        [Paragraph("CASE ID", s["Label"]), Paragraph(f'<font name="{MONO}" size="8"><b>{esc(case_id)}</b></font>', s["Value"])],
        [Paragraph("ANALYZED", s["Label"]), Paragraph(f'<font name="{MONO}" size="8">{esc(format_date(analyzed_at) or DASH)}</font>', s["Value"])],
        [Paragraph("CLASSIFICATION", s["Label"]),
         Paragraph(f'<font color="{fg.hexval()}"><b>{esc(verdict)}</b></font>', s["Value"])],
        [Paragraph("REPORT TYPE", s["Label"]), Paragraph("Email forensics / SOC triage", s["Value"])],
    ]
    ident = Table(ident_rows, colWidths=[26 * mm, 44 * mm], hAlign="RIGHT")
    ident.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 2.0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.0),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ]))

    left = [
        Paragraph("CONFIDENTIAL FORENSIC CASE REPORT", s["ReportKicker"]),
        Spacer(1, 2.2 * mm),
        Paragraph("MailGuard Security Report", s["ReportTitle"]),
        Spacer(1, 1.4 * mm),
        Paragraph("Digital forensics and email threat analysis for SOC incident response",
                  s["ReportSubtitle"]),
    ]
    head = Table([[left, ident]], colWidths=[CONTENT_W - 74 * mm, 74 * mm], hAlign="LEFT")
    head.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    rule = Table([[""]], colWidths=[CONTENT_W], rowHeights=[1.9 * mm])
    rule.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [head, Spacer(1, 2.6 * mm), rule, Spacer(1, GAP_SECTION)]


def _closing(s):
    bar = Table([[""]], colWidths=[CONTENT_W], rowHeights=[0.7 * mm])
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY)]))
    return [Spacer(1, 6 * mm), bar, Spacer(1, 2.4 * mm),
            Paragraph("END OF REPORT — the sections above constitute the complete "
                      "generated record for this case.", s["Caption"])]


def build_case_pdf(case: dict) -> bytes:
    """Render the case record to PDF bytes (public entry point, unchanged).

    The document is composed twice so the running foot can print
    "Page n of N"; a third pass only runs if a page count changes the flow.
    """
    _first, total = _compose_pdf(case, None)
    payload, check = _compose_pdf(case, total)
    if check != total:
        payload, _check = _compose_pdf(case, check)
    return payload


def _compose_pdf(case: dict, page_total):
    s = styles()
    buf = BytesIO()

    # Margins are inset by the frame's own padding (see _frame_padding) so the
    # rendered grid matches MARGIN_*/CONTENT_W to the point.
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=MARGIN_R - FRAME_PAD, leftMargin=MARGIN_L - FRAME_PAD,
        topMargin=MARGIN_T - FRAME_PAD, bottomMargin=MARGIN_B - FRAME_PAD,
        title="MailGuard Security Report",
        author="MailGuard",
        subject="Email Threat Detection and Forensic Intelligence Report",
    )
    doc._mailguard_meta = {}

    case_id = case.get("caseId", "UNASSIGNED")
    score = case.get("riskScore", 0)
    severity = case.get("severity", "")
    analyzed_at = case.get("analyzedAt", "")
    case_hash = case.get("caseHash", "")
    previous_hash = case.get("previousHash")

    checks = case.get("headerChecks") or {}
    ai = case.get("aiSignals") or {}
    origin = case.get("origin") or {}
    analysis = case.get("analysis") or {}
    metadata = analysis.get("metadata") or {}
    urls = analysis.get("urls") or []
    attachments = analysis.get("attachments") or []
    dashboard = case.get("dashboard") or {}
    trace = case.get("origin_trace") or {}
    related = case.get("relatedCases") or []

    fg, bg, verdict = severity_palette(severity or score)
    tone = tone_of(verdict)
    findings = collect_findings(case, trace)
    action, action_fg, action_bg, action_text = recommendation(score, findings)
    summary = ai.get("summary") or (
        f"MailGuard assigned a risk score of {score}/100. "
        f"The message contains {len(findings)} recorded security finding(s), "
        f"{len(urls)} extracted URL(s), and {len(attachments)} attachment(s)."
    )

    doc._mailguard_meta = {
        "case_id": case_id,
        "verdict": verdict,
        "tone": tone,
        "page_total": page_total,
    }

    story = []

    # ---- masthead -------------------------------------------------------
    story += _masthead(case_id, analyzed_at, verdict, fg, s)

    # ---- 01 case overview ----------------------------------------------
    story += [
        section_heading("01", "CASE OVERVIEW", s, NAVY),
        Spacer(1, GAP_BLOCK),
        _risk_block(score, verdict, fg, findings, urls, attachments, s),
        Spacer(1, GAP_BLOCK),
        note_block("EXECUTIVE ASSESSMENT", summary, s, tone),
        Spacer(1, GAP_SECTION),
    ]

    # ---- 02 email information ------------------------------------------
    story += [
        section_heading("02", "EMAIL INFORMATION", s, BLUE),
        Spacer(1, GAP_BLOCK),
        kv([
            ("From", metadata.get("from") or ""),
            ("To", metadata.get("to") or ""),
            ("Reply-To", metadata.get("reply_to") or ""),
            ("Subject", metadata.get("subject") or ""),
            ("Date", metadata.get("date") or ""),
            ("Message-ID", metadata.get("message_id") or "", "mono"),
            ("Return-Path", metadata.get("return_path") or "", "mono"),
        ], s),
        Spacer(1, GAP_SECTION),
    ]

    # ---- 03 authentication ---------------------------------------------
    auth_widths = [40 * mm, 36 * mm, CONTENT_W - 76 * mm]
    auth_rows = [[Paragraph("CHECK", s["TH"]), Paragraph("RESULT", s["TH"]),
                  Paragraph("ASSESSMENT", s["TH"])]]
    for name, value, assessment in [
        ("SPF", checks.get("spf", "none"), "Sender authorization result."),
        ("DKIM", checks.get("dkim", "none"), "Message signature verification."),
        ("DMARC", checks.get("dmarc", "none"), "Domain authentication / alignment."),
        ("Domain", "MISMATCH" if checks.get("senderDomainMismatch") else "MATCH",
         "From-domain vs. Reply-To domain."),
    ]:
        auth_rows.append([
            P(name, s, "TBStrong"),
            auth_badge(value, s) if name != "Domain" else (
                status_label("MISMATCH", "red", s, 26 * mm) if checks.get("senderDomainMismatch")
                else status_label("MATCH", "green", s, 26 * mm)
            ),
            P(assessment, s, "TB"),
        ])
    story += [
        section_heading("03", "AUTHENTICATION", s, TEAL),
        Spacer(1, GAP_BLOCK),
        forensic_table(auth_rows, auth_widths, s, valign="MIDDLE"),
        Spacer(1, GAP_TIGHT),
        Paragraph("Results are the stored header-check values; the renderer does not recompute "
                  "SPF, DKIM or DMARC verdicts.", s["Caption"]),
    ]

    # ---- 04 origin & route ---------------------------------------------
    story += [PageBreak(), section_heading("04", "ORIGIN & ROUTE ANALYSIS", s, AMBER),
              Spacer(1, GAP_BLOCK)]
    hops = trace.get("hops") or []
    first_public = next((h for h in hops if h.get("ip") and not h.get("internal")), None)
    first_blacklist = (first_public or {}).get("blacklist") or {}
    abuse = first_blacklist.get("abuse_score")
    if abuse is None:
        abuse = origin.get("abuse_score")
    story += [
        sub_head("ORIGIN METADATA", s),
        Spacer(1, GAP_TIGHT),
        field_grid([
            ("Origin IP", origin.get("ip") or "Not identified"),
            ("Location", " / ".join(str(v) for v in
                                    (origin.get("city"), origin.get("country")) if v) or DASH),
            ("ISP", origin.get("isp") or DASH),
            ("ASN", origin.get("asn") or DASH),
            ("Hosting / VPN", "YES" if origin.get("hosting") or origin.get("proxy")
                              or origin.get("isVpnOrHosting") else "NO"),
            ("Blacklist", "LISTED" if origin.get("blacklisted") or first_blacklist.get("listed")
                          else "NOT LISTED"),
            ("rDNS", origin.get("reverse") or origin.get("hostname") or DASH),
            ("Abuse score", abuse if abuse is not None else DASH),
        ], s, mono_keys={"Origin IP", "rDNS", "ASN"}),
        Spacer(1, GAP_ROUTE),
    ]
    if hops:
        story += [
            sub_head("RECEIVED HOP TABLE", s, "PRIMARY ROUTE EVIDENCE"),
            Spacer(1, GAP_TIGHT),
            render_hops(hops, s),
            Spacer(1, GAP_ROUTE),
            sub_head("ROUTE VISUALISATION", s, "SUMMARY VIEW"),
            Spacer(1, GAP_TIGHT),
        ]
        story += [render_trace(hops, s)]
        story += [Spacer(1, GAP_ROUTE), sub_head("FORENSIC TIMELINE", s, "STORED TIMESTAMPS"),
                  Spacer(1, GAP_TIGHT), render_timeline(hops, metadata, analyzed_at, s),
                  Spacer(1, GAP_TIGHT), Paragraph(_route_notes(hops, first_public), s["Caption"]),
                  Spacer(1, GAP_SECTION)]
    else:
        story += [Spacer(1, GAP_TIGHT),
                  kv([("Received route", "No public Received-chain hops were available.")], s, AMBER),
                  Spacer(1, GAP_SECTION)]

    # ---- 05 security findings ------------------------------------------
    story += [CondPageBreak(70 * mm), section_heading("05", "SECURITY FINDINGS", s, RED),
              Spacer(1, GAP_BLOCK), render_findings(findings, s),
              Spacer(1, GAP_TIGHT),
              Paragraph("Severity colour marks the finding status only. Findings are the stored "
                        "case findings, header-check deltas and per-hop origin flags.", s["Caption"]),
              Spacer(1, GAP_SECTION),
    ]

    # ---- 06 urls / 07 attachments / 08 ai / 09 action ------------------
    story += [
        CondPageBreak(46 * mm),
        section_heading("06", "URL ANALYSIS", s, BLUE),
        Spacer(1, GAP_BLOCK),
        render_urls(urls, dashboard, s),
        Spacer(1, GAP_SECTION),
        CondPageBreak(46 * mm),
        section_heading("07", "ATTACHMENTS", s, PURPLE),
        Spacer(1, GAP_BLOCK),
        render_attachments(attachments, s),
        Spacer(1, GAP_SECTION),
        CondPageBreak(46 * mm),
        section_heading("08", "AI / ANALYST EXPLANATION", s, VIOLET),
        Spacer(1, GAP_BLOCK),
        note_block("ANALYST NARRATIVE", ai.get("summary") or summary, s, "navy"),
        Spacer(1, GAP_SECTION),
        CondPageBreak(46 * mm),
        section_heading("09", "RECOMMENDED ACTION", s, action_fg),
        Spacer(1, GAP_BLOCK),
    ]
    action_block = Table([[
        [Paragraph("DISPOSITION", s["Label"]), Spacer(1, 1.2 * mm),
         status_label(action, _action_tone(action), s, 52 * mm, align="left")],
        [Paragraph("BASIS", s["Label"]), Spacer(1, 1.2 * mm),
         wrapped(action_text, s, "Body", CONTENT_W - 72 * mm - 20)],
    ]], colWidths=[72 * mm, CONTENT_W - 72 * mm], hAlign="LEFT")
    action_block.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.5, BOX),
        ("LINEBEFORE", (0, 0), (0, -1), 1.7, action_fg),
        ("LINEAFTER", (0, 0), (0, -1), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6.5),
    ]))
    story += [action_block, Spacer(1, GAP_SECTION)]

    # ---- 10 evidence & integrity ----------------------------------------
    # Section 10 is the closing record page: it starts a fresh page whenever
    # less than one page of space is left, so the integrity block never
    # strands half its structure at the foot of the previous page.
    story += [CondPageBreak(150 * mm),
              section_heading("10", "EVIDENCE & INTEGRITY RECORD", s, SLATE),
              Spacer(1, GAP_BLOCK)]

    # hashes are technical evidence: monospaced, width-aware, never clipped
    left_w = 112 * mm
    right_w = CONTENT_W - left_w
    hash_w = left_w - 42 * mm - 14
    ids_rows, ids_cmds = [], [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, BOX),
        ("BACKGROUND", (0, 0), (0, -1), PANEL),
        ("LINEBELOW", (0, 0), (-1, -2), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6.0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6.0),
    ]
    for idx, (label, value) in enumerate([
        ("EVIDENCE SHA-256\nCASE HASH", case_hash),
        ("PREVIOUS HASH", previous_hash),
        ("CASE ID", case_id),
        ("ANALYSIS TIMESTAMP", format_date(analyzed_at) or DASH),
        ("RELATED CASES", f"{len(related)} recorded" if not related else
                          ", ".join(str(r) for r in related)),
    ]):
        lines = str(label).split("\n")
        label_cell = [Paragraph(esc(ln), s["Label"]) for ln in lines]
        ids_rows.append([label_cell,
                         wrapped(labelled(value), s, "Mono", hash_w, mode="mono")])
        if idx % 2 == 1:
            ids_cmds.append(("BACKGROUND", (1, idx), (1, idx), ZEBRA))
    ids_tbl = Table(ids_rows, colWidths=[42 * mm, left_w - 42 * mm], hAlign="LEFT")
    ids_tbl.setStyle(TableStyle(ids_cmds))

    count_rows = []
    for name, value in (("RECEIVED HOPS", len(hops)), ("SECURITY FINDINGS", len(findings)),
                        ("URLS", len(urls)), ("ATTACHMENTS", len(attachments)),
                        ("RELATED CASES", len(related))):
        count_rows.append([Paragraph(esc(name), s["Label"]),
                           Paragraph(esc(value), s["StatValue"])])
    counts_tbl = Table(count_rows, colWidths=[right_w - 26 * mm, 26 * mm], hAlign="RIGHT")
    counts_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("BOX", (0, 0), (-1, -1), 0.5, BOX),
        ("LINEBELOW", (0, 0), (-1, -2), 0.35, LINE),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.4),
    ]))

    story += [
        Table([[
            [sub_head("IDENTIFIERS  /  CASE METADATA", s, None, width=left_w),
             Spacer(1, GAP_TIGHT), ids_tbl],
            [sub_head("EVIDENCE COUNTS", s, None, width=right_w),
             Spacer(1, GAP_TIGHT), counts_tbl],
        ]], colWidths=[left_w, right_w], hAlign="LEFT",
            style=TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ])),
        Spacer(1, GAP_BLOCK),
    ]

    half_w = (CONTENT_W - 10) / 2.0
    blocks = [
        ("INTEGRITY CONTROL",
         "Every value in this report is read from the stored case record and escaped before "
         "rendering; the renderer recomputes no hash, no geolocation and no authentication "
         "verdict. The case hash and the previous hash form the chain of custody for the record "
         "shown here: a mismatch against the stored record means this report was not produced "
         "from that record."),
        ("REPORT SCOPE",
         "Sections 01 to 10 cover the parsed message metadata, header authentication checks, "
         "origin and Received routing evidence, security findings, URL and attachment results, "
         "the AI / analyst explanation and the recommended disposition. IP geolocation is "
         "approximate, and external reputation or blocklist results are absent where they were "
         "not stored with the case. A risk score breakdown is intentionally excluded."),
        ("HANDLING",
         "Confidential investigative material. Distribution is limited to incident responders "
         "and reviewers acting on this case. The report reproduces stored values only and does "
         "not attach the source message or its artefacts; retain the original .eml alongside the "
         "case record."),
    ]
    story += [sub_head(blocks[0][0], s), Spacer(1, GAP_TIGHT),
              Table([[wrapped(blocks[0][1], s, "Small", CONTENT_W - 14)]],
                    colWidths=[CONTENT_W], hAlign="LEFT",
                    style=TableStyle([
                        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 6.0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6.0),
                    ])),
              Spacer(1, GAP_BLOCK)]
    side_cells = []
    for title, body in blocks[1:]:
        side_cells.append([sub_head(title, s, None, width=half_w - 14),
                           Spacer(1, GAP_TIGHT),
                           wrapped(body, s, "Small", half_w - 14)])
    story += [
        Table([[side_cells[0], side_cells[1]]], colWidths=[half_w, half_w], hAlign="LEFT",
              style=TableStyle([
                  ("VALIGN", (0, 0), (-1, -1), "TOP"),
                  ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                  ("LINEAFTER", (0, 0), (0, 0), 0.5, LINE),
                  ("LEFTPADDING", (0, 0), (-1, -1), 7),
                  ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                  ("TOPPADDING", (0, 0), (-1, -1), 6),
                  ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
              ])),
    ]

    story += _closing(s)

    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    buf.seek(0)
    data = buf.read()
    return data, doc.page