"""
Epic 4 — reporting: downloadable PDF case file.

Owner: whoever is assigned Epic 4 in OWNERSHIP.md.
Remember to run any email-derived text through
`app.core.security.escape_for_report` before it goes into the PDF.

CONTRACT:
    build_case_pdf(case: dict) -> bytes
        `case` is shaped like schemas.AnalyzeResponse (see
        app/models/schemas.py), plus two convenience keys the report
        route adds before calling this function:
            analyzedAt    (str)         - ISO timestamp, from the store record
            previousHash  (str | None)  - previous case's hash in the chain
        Returns raw PDF bytes.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.core.security import escape_for_report


# ============================================================
# MailGuard REPORT PALETTE
# ============================================================

NAVY = colors.HexColor("#101827")
BLUE = colors.HexColor("#2563EB")
PURPLE = colors.HexColor("#7C3AED")
PURPLE_SOFT = colors.HexColor("#F2ECFF")
RED = colors.HexColor("#DC2626")
RED_SOFT = colors.HexColor("#FDECEC")
AMBER = colors.HexColor("#CA8A04")
AMBER_SOFT = colors.HexColor("#FFF8DD")
GREEN = colors.HexColor("#15803D")
GREEN_SOFT = colors.HexColor("#EAF8EF")
CYAN = colors.HexColor("#0891B2")
INK = colors.HexColor("#18212F")
MUTED = colors.HexColor("#687386")
LIGHT = colors.HexColor("#F4F6F8")
LINE = colors.HexColor("#DCE1E8")
WHITE = colors.white


def esc(value) -> str:
    """Run any potentially email-derived value through the shared escaper."""
    if value is None:
        return ""
    return escape_for_report(str(value))


def severity_palette(severity):
    value = str(severity or "").strip().lower()
    if value == "red":
        return RED, RED_SOFT, "HIGH RISK"
    if value == "yellow":
        return AMBER, AMBER_SOFT, "MEDIUM RISK"
    if value == "green":
        return GREEN, GREEN_SOFT, "LOW RISK"
    return MUTED, LIGHT, "UNKNOWN"


def auth_palette(value):
    v = str(value or "").strip().lower()
    if v == "pass":
        return GREEN, GREEN_SOFT
    if v == "fail":
        return RED, RED_SOFT
    return MUTED, LIGHT


def urgency_palette(value):
    v = str(value or "").strip().lower()
    if v == "high":
        return RED, RED_SOFT
    if v == "medium":
        return AMBER, AMBER_SOFT
    return GREEN, GREEN_SOFT


def get_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle", fontName="Helvetica-Bold", fontSize=21,
        leading=24, textColor=INK,
    ))
    styles.add(ParagraphStyle(
        name="Subtitle", fontName="Helvetica", fontSize=8.5,
        leading=12, textColor=MUTED,
    ))
    styles.add(ParagraphStyle(
        name="Section", fontName="Helvetica-Bold", fontSize=12,
        leading=15, textColor=INK, spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="Label", fontName="Helvetica-Bold", fontSize=7.2,
        leading=9, textColor=MUTED, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="Value", fontName="Helvetica", fontSize=9,
        leading=12, textColor=INK,
    ))
    styles.add(ParagraphStyle(
        name="Body", fontName="Helvetica", fontSize=8.5,
        leading=13, textColor=INK,
    ))
    styles.add(ParagraphStyle(
        name="Small", fontName="Helvetica", fontSize=7.5,
        leading=10, textColor=MUTED,
    ))
    styles.add(ParagraphStyle(
        name="TableHeader", fontName="Helvetica-Bold", fontSize=7.2,
        leading=9, textColor=WHITE,
    ))
    styles.add(ParagraphStyle(
        name="TableBody", fontName="Helvetica", fontSize=7.8,
        leading=11, textColor=INK,
    ))
    styles.add(ParagraphStyle(
        name="Risk", fontName="Helvetica-Bold", fontSize=27,
        leading=29, textColor=RED, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="Badge", fontName="Helvetica-Bold", fontSize=7.5,
        leading=9, alignment=TA_CENTER,
    ))

    return styles


def P(value, styles, style="Value"):
    return Paragraph(esc(value), styles[style])


def badge(text, fg, bg, styles, width=30 * mm):
    p = Paragraph(
        f'<font color="{fg.hexval()}"><b>{esc(text)}</b></font>',
        styles["Badge"],
    )
    t = Table([[p]], colWidths=[width], rowHeights=[7 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.5, fg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def key_value_table(rows, styles, accent=BLUE):
    data = [[P(k, styles, "Label"), P(v, styles, "Value")] for k, v in rows]
    table = Table(data, colWidths=[46 * mm, 134 * mm], repeatRows=0)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBEFORE", (0, 0), (0, -1), 2, accent),
    ]))
    return table


def section_heading(number, title, styles, color=BLUE):
    number_cell = Table(
        [[Paragraph(f'<font color="{WHITE.hexval()}"><b>{esc(number)}</b></font>', styles["Badge"])]],
        colWidths=[9 * mm], rowHeights=[8 * mm],
    )
    number_cell.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    heading = Table(
        [[number_cell, Paragraph(esc(title), styles["Section"])]],
        colWidths=[11 * mm, 169 * mm],
    )
    heading.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return heading


def risk_bar(score, accent):
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))
    filled = max(1, int(150 * score / 100))
    remaining = max(1, 150 - filled)

    bar = Table([["", ""]], colWidths=[filled * mm, remaining * mm], rowHeights=[4 * mm])
    bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), accent),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#E5E7EB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return bar


def draw_background(canvas, document):
    canvas.saveState()
    width, height = A4

    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 24 * mm, width, 24 * mm, stroke=0, fill=1)
    canvas.setFillColor(RED)
    canvas.rect(0, height - 24 * mm, 5 * mm, 24 * mm, stroke=0, fill=1)

    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, width, 13 * mm, stroke=0, fill=1)

    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(WHITE)
    canvas.drawString(18 * mm, 5.2 * mm, "MailGuard  /  FORENSIC REPORT ENGINE")

    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(192 * mm, 5.2 * mm, f"PAGE {document.page}")

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(18 * mm, height - 10 * mm, "MailGuard")

    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#C9D2E1"))
    canvas.drawString(18 * mm, height - 16 * mm, "EMAIL THREAT DETECTION  •  FORENSIC INTELLIGENCE REPORT")

    canvas.restoreState()


def build_case_pdf(case: dict) -> bytes:
    styles = get_styles()
    pdf_buffer = BytesIO()

    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=31 * mm,
        bottomMargin=18 * mm,
        title="MailGuard Case Report",
        author="MailGuard",
        subject="Email Threat Detection & Forensic Intelligence Report",
    )

    story = []

    case_id = case.get("caseId", "UNASSIGNED")
    risk_score = case.get("riskScore", 0)
    severity = case.get("severity", "green")
    analyzed_at = case.get("analyzedAt", "")
    case_hash = case.get("caseHash", "")
    previous_hash = case.get("previousHash")

    header_checks = case.get("headerChecks") or {}
    ai_signals = case.get("aiSignals") or {}
    origin = case.get("origin") or {}
    related_cases = case.get("relatedCases") or []
    analysis = case.get("analysis") or {}
    metadata = analysis.get("metadata") or {}

    severity_fg, severity_bg, severity_label = severity_palette(severity)

    # ------------------------------------------------------------
    # Intro band
    # ------------------------------------------------------------
    story.append(Spacer(1, 3 * mm))

    intro_left = [
        Paragraph(
            '<font color="#DC2626" size="8"><b>CONFIDENTIAL</b></font>',
            styles["Small"],
        ),
        Spacer(1, 1.5 * mm),
        Paragraph("SECURITY CASE REPORT", styles["ReportTitle"]),
        Spacer(1, 1 * mm),
        Paragraph("Email Threat Detection &amp; Forensic Intelligence", styles["Subtitle"]),
    ]

    intro = Table(
        [[
            intro_left,
            Paragraph(
                '<font color="#687386" size="7"><b>CASE ID</b></font><br/>'
                f'<font size="11"><b>{esc(case_id)}</b></font><br/><br/>'
                '<font color="#687386" size="7"><b>ANALYZED AT</b></font><br/>'
                f'<font size="8">{esc(analyzed_at)}</font>',
                styles["Body"],
            ),
        ]],
        colWidths=[119 * mm, 61 * mm],
    )
    intro.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("LINEBEFORE", (0, 0), (0, 0), 4, RED),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(intro)
    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------
    # Risk summary
    # ------------------------------------------------------------
    risk_panel = Table(
        [[
            [
                Paragraph("FRAUD RISK SCORE", styles["Label"]),
                Paragraph(
                    f'<font color="{severity_fg.hexval()}"><b>{esc(risk_score)}</b></font>'
                    '<font color="#687386" size="9"> / 100</font>',
                    styles["Risk"],
                ),
                risk_bar(risk_score, severity_fg),
                Spacer(1, 2 * mm),
                Paragraph("Higher score indicates stronger fraud/phishing risk.", styles["Small"]),
            ],
            [
                Paragraph("THREAT CLASSIFICATION", styles["Label"]),
                badge(severity_label, severity_fg, severity_bg, styles, width=38 * mm),
                Spacer(1, 3 * mm),
                Paragraph("Automated classification based on analysis signals.", styles["Small"]),
            ],
        ]],
        colWidths=[110 * mm, 70 * mm],
    )
    risk_panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F7FAFF")),
        ("BACKGROUND", (1, 0), (1, 0), severity_bg),
        ("BOX", (0, 0), (-1, -1), 0.8, LINE),
        ("LINEBEFORE", (1, 0), (1, 0), 0.7, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(risk_panel)
    story.append(Spacer(1, 7 * mm))

    # ------------------------------------------------------------
    # 01. Case information
    # ------------------------------------------------------------
    story.append(section_heading("01", "CASE INFORMATION", styles, BLUE))
    story.append(key_value_table(
        [
            ("Case ID", case_id),
            ("Analyzed At", analyzed_at),
            ("Current Case Hash", case_hash),
            ("Previous Case Hash", previous_hash or "— (first case in chain)"),
        ],
        styles, BLUE,
    ))
    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------
    # 02. Email forensics
    # ------------------------------------------------------------
    story.append(section_heading("02", "EMAIL FORENSICS", styles, CYAN))
    story.append(key_value_table(
        [
            ("From", metadata.get("from", "")),
            ("Reply-To", metadata.get("reply_to", "")),
            ("To", metadata.get("to", "")),
            ("Subject", metadata.get("subject", "")),
            ("Date", metadata.get("date", "")),
        ],
        styles, CYAN,
    ))
    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------
    # 03. Header security checks
    # ------------------------------------------------------------
    story.append(section_heading("03", "HEADER SECURITY CHECKS", styles, GREEN))

    header_rows = [
        ("SPF", header_checks.get("spf", "none"), "Sender authorization check"),
        ("DKIM", header_checks.get("dkim", "none"), "Message signature verification"),
        ("DMARC", header_checks.get("dmarc", "none"), "Domain authentication / alignment"),
        (
            "Sender Domain Mismatch",
            "yes" if header_checks.get("senderDomainMismatch") else "no",
            "From-domain vs. reply-to domain mismatch",
        ),
    ]

    data = [[
        Paragraph("CHECK", styles["TableHeader"]),
        Paragraph("RESULT", styles["TableHeader"]),
        Paragraph("ASSESSMENT", styles["TableHeader"]),
    ]]

    for name, result, assessment in header_rows:
        fg, bg = auth_palette(result) if name != "Sender Domain Mismatch" else (
            (RED, RED_SOFT) if result == "yes" else (GREEN, GREEN_SOFT)
        )
        data.append([
            P(name, styles, "TableBody"),
            badge(result.upper(), fg, bg, styles, width=26 * mm),
            P(assessment, styles, "TableBody"),
        ])

    security_table = Table(data, colWidths=[48 * mm, 35 * mm, 97 * mm], repeatRows=1)
    security_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY),
        ("LINEBELOW", (0, 1), (-1, -1), 0.45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            security_commands.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FAFBFC")))
    security_table.setStyle(TableStyle(security_commands))
    story.append(security_table)
    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------
    # 04. AI threat analysis
    # ------------------------------------------------------------
    story.append(section_heading("04", "AI THREAT ANALYSIS", styles, PURPLE))

    urgency = ai_signals.get("urgencyLanguage", "low")
    urgency_fg, urgency_bg = urgency_palette(urgency)
    impersonation_score = ai_signals.get("impersonationScore", 0)
    ai_summary = ai_signals.get("summary", "")

    ai_top = Table(
        [[
            [
                Paragraph("URGENCY LANGUAGE", styles["Label"]),
                badge(str(urgency).upper(), urgency_fg, urgency_bg, styles, width=28 * mm),
            ],
            [
                Paragraph("IMPERSONATION SCORE", styles["Label"]),
                Paragraph(
                    f'<font color="{PURPLE.hexval()}" size="18"><b>{esc(impersonation_score)}</b></font>'
                    '<font color="#687386"> / 100</font>',
                    styles["Body"],
                ),
            ],
        ]],
        colWidths=[90 * mm, 90 * mm],
    )
    ai_top.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PURPLE_SOFT),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D9C9FF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.append(ai_top)
    story.append(Spacer(1, 3 * mm))

    ai_summary_box = Table(
        [[
            Paragraph("AI ANALYSIS SUMMARY", styles["Label"]),
            Paragraph(esc(ai_summary) if ai_summary else "No AI summary available.", styles["Body"]),
        ]],
        colWidths=[42 * mm, 138 * mm],
    )
    ai_summary_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FAF8FF")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D9C9FF")),
        ("LINEBEFORE", (0, 0), (0, -1), 3, PURPLE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(ai_summary_box)
    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------
    # 05. Origin & attribution
    # ------------------------------------------------------------
    story.append(section_heading("05", "ORIGIN & ATTRIBUTION", styles, colors.HexColor("#EA580C")))

    is_vpn = origin.get("isVpnOrHosting", False)
    vpn_fg, vpn_bg = (RED, RED_SOFT) if is_vpn else (GREEN, GREEN_SOFT)

    lat = origin.get("lat")
    lng = origin.get("lng")
    coords = f"{lat}, {lng}" if lat is not None and lng is not None else "—"

    origin_table = Table(
        [[
            P("ORIGIN IP", styles, "Label"),
            P("COUNTRY / CITY", styles, "Label"),
            P("COORDINATES", styles, "Label"),
            P("VPN / HOSTING", styles, "Label"),
        ], [
            Paragraph(esc(origin.get("ip", "")), styles["Value"]),
            Paragraph(esc(f"{origin.get('country') or '—'} / {origin.get('city') or '—'}"), styles["Value"]),
            Paragraph(esc(coords), styles["Value"]),
            badge("YES" if is_vpn else "NO", vpn_fg, vpn_bg, styles, width=20 * mm),
        ]],
        colWidths=[45 * mm, 55 * mm, 40 * mm, 40 * mm],
    )
    origin_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(origin_table)
    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------
    # 06. Related cases
    # ------------------------------------------------------------
    story.append(section_heading("06", "RELATED CASES", styles, BLUE))

    if related_cases:
        data = [[
            Paragraph("CASE ID", styles["TableHeader"]),
            Paragraph("SIMILARITY", styles["TableHeader"]),
            Paragraph("MATCHED ON", styles["TableHeader"]),
        ]]
        for related in related_cases:
            similarity = related.get("similarity", 0)
            try:
                similarity = f"{float(similarity):.2f}"
            except (TypeError, ValueError):
                similarity = str(similarity)
            matched_on = ", ".join(related.get("matchedOn") or [])
            data.append([
                P(related.get("caseId", ""), styles, "TableBody"),
                P(similarity, styles, "TableBody"),
                P(matched_on, styles, "TableBody"),
            ])

        related_table = Table(data, colWidths=[50 * mm, 35 * mm, 95 * mm], repeatRows=1)
        related_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY),
            ("LINEBELOW", (0, 1), (-1, -1), 0.45, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]
        for i in range(1, len(data)):
            if i % 2 == 0:
                related_commands.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FAFBFC")))
        related_table.setStyle(TableStyle(related_commands))
        story.append(related_table)
    else:
        empty = Table(
            [[
                Paragraph("NO RELATED CASES FOUND", styles["Value"]),
                Paragraph("No matching historical case records were found.", styles["Small"]),
            ]],
            colWidths=[55 * mm, 125 * mm],
        )
        empty.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.6, LINE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ]))
        story.append(empty)

    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------
    # 07. Case integrity
    # ------------------------------------------------------------
    story.append(section_heading("07", "CASE INTEGRITY", styles, NAVY))
    story.append(key_value_table(
        [
            ("Previous Case Hash", previous_hash or "— (first case in chain)"),
            ("Current Case Hash", case_hash),
            ("Integrity Model", "Hash-chained case record (tamper-evident record chain)"),
        ],
        styles, NAVY,
    ))
    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------
    # 08. Analyst conclusion
    # ------------------------------------------------------------
    story.append(section_heading("08", "ANALYST CONCLUSION", styles, RED))

    conclusion = (
        f"The analyzed email received a fraud risk score of "
        f"{esc(risk_score)}/100 and was classified as "
        f"<b>{esc(severity_label)}</b>. This report consolidates "
        f"authentication checks, AI content signals, origin information, "
        f"related-case matches, and case-integrity information."
    )
    conclusion_box = Table([[Paragraph(conclusion, styles["Body"])]], colWidths=[180 * mm])
    conclusion_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7F7")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#F3C1C1")),
        ("LINEBEFORE", (0, 0), (0, -1), 4, RED),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
    ]))
    story.append(conclusion_box)
    story.append(Spacer(1, 4 * mm))

    note = Table(
        [[
            Paragraph("<b>SECURITY NOTE</b>", styles["Label"]),
            Paragraph("Email-derived values are treated as untrusted data and rendered as escaped plain text.", styles["Small"]),
        ]],
        colWidths=[32 * mm, 148 * mm],
    )
    note.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
    ]))
    story.append(note)

    document.build(story, onFirstPage=draw_background, onLaterPages=draw_background)

    pdf_buffer.seek(0)
    return pdf_buffer.read()
