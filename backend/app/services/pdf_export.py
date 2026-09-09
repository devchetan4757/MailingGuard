"""MailGuard PDF security report generator.

Keeps the existing Report Generation page/API contract while changing only
the generated PDF content.

Report sections:
1. Executive Summary
2. Email Information
3. Authentication
4. Origin & Route Analysis
5. Security Findings
6. URL Analysis
7. Attachments
8. AI / Analyst Explanation
9. Recommended Action
10. Forensic / Audit Data

Risk Score Breakdown is intentionally excluded.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.security import escape_for_report


NAVY = colors.HexColor("#101827")
BLUE = colors.HexColor("#2563EB")
CYAN = colors.HexColor("#0891B2")
PURPLE = colors.HexColor("#7C3AED")
ORANGE = colors.HexColor("#EA580C")
RED = colors.HexColor("#DC2626")
RED_SOFT = colors.HexColor("#FDECEC")
AMBER = colors.HexColor("#CA8A04")
AMBER_SOFT = colors.HexColor("#FFF8DD")
GREEN = colors.HexColor("#15803D")
GREEN_SOFT = colors.HexColor("#EAF8EF")
LIGHT = colors.HexColor("#F4F6F8")
LIGHT_BLUE = colors.HexColor("#F7FAFF")
LIGHT_PURPLE = colors.HexColor("#FAF8FF")
LINE = colors.HexColor("#DCE1E8")
INK = colors.HexColor("#18212F")
MUTED = colors.HexColor("#687386")
WHITE = colors.white


def esc(value: Any) -> str:
    return "" if value is None else escape_for_report(str(value))


def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="ReportTitle", fontName="Helvetica-Bold", fontSize=21,
                          leading=24, textColor=INK))
    s.add(ParagraphStyle(name="Subtitle", fontName="Helvetica", fontSize=8.5,
                          leading=12, textColor=MUTED))
    s.add(ParagraphStyle(name="Section", fontName="Helvetica-Bold", fontSize=12,
                          leading=15, textColor=INK, spaceAfter=6))
    s.add(ParagraphStyle(name="Label", fontName="Helvetica-Bold", fontSize=7.2,
                          leading=9, textColor=MUTED))
    s.add(ParagraphStyle(name="Value", fontName="Helvetica", fontSize=8.8,
                          leading=12, textColor=INK))
    s.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=8.5,
                          leading=13, textColor=INK))
    s.add(ParagraphStyle(name="Small", fontName="Helvetica", fontSize=7.4,
                          leading=10, textColor=MUTED))
    s.add(ParagraphStyle(name="TH", fontName="Helvetica-Bold", fontSize=7.2,
                          leading=9, textColor=WHITE))
    s.add(ParagraphStyle(name="TB", fontName="Helvetica", fontSize=7.5,
                          leading=10, textColor=INK))
    s.add(ParagraphStyle(name="Center", fontName="Helvetica", fontSize=7.5,
                          leading=10, textColor=MUTED, alignment=TA_CENTER))
    return s


def P(value, s, style="Value"):
    return Paragraph(esc(value), s[style])


def badge(text, fg, bg, s, width=30 * mm):
    p = Paragraph(
        f'<font color="{fg.hexval()}"><b>{esc(text)}</b></font>',
        s["Center"],
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


def section_heading(number, title, s, color=BLUE):
    n = Table([[Paragraph(
        f'<font color="{WHITE.hexval()}"><b>{esc(number)}</b></font>', s["Center"]
    )]], colWidths=[9 * mm], rowHeights=[8 * mm])
    n.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    h = Table([[n, Paragraph(esc(title), s["Section"])]],
              colWidths=[11 * mm, 169 * mm])
    h.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return h


def kv(rows, s, accent=BLUE):
    t = Table([[P(k, s, "Label"), P(v, s)] for k, v in rows],
              colWidths=[48 * mm, 132 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.45, LINE),
        ("LINEBEFORE", (0, 0), (0, -1), 2, accent),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


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
        return badge("PASS", GREEN, GREEN_SOFT, s, 27 * mm)
    if v in {"fail", "softfail", "permerror", "temperror", "mismatch"}:
        return badge(v.upper(), RED, RED_SOFT, s, 27 * mm)
    if v == "match":
        return badge("MATCH", GREEN, GREEN_SOFT, s, 27 * mm)
    return badge(v.upper(), MUTED, LIGHT, s, 27 * mm)


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


def render_findings(findings, s):
    if not findings:
        return kv([("Status", "No explicit security findings were recorded.")], s, GREEN)

    rows = [[Paragraph("SEVERITY", s["TH"]), Paragraph("SIGNAL", s["TH"]),
             Paragraph("EVIDENCE", s["TH"])]]
    for f in findings:
        sev = str(f["severity"]).upper()
        if sev == "HIGH":
            fg, bg = RED, RED_SOFT
        elif sev in {"MEDIUM", "MODERATE"}:
            fg, bg = AMBER, AMBER_SOFT
        else:
            fg, bg = GREEN, GREEN_SOFT
        rows.append([
            badge(sev, fg, bg, s, 24 * mm),
            P(f["signal"], s, "TB"),
            P(f["message"], s, "TB"),
        ])
    t = Table(rows, colWidths=[28 * mm, 48 * mm, 104 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY),
        ("LINEBELOW", (0, 1), (-1, -1), 0.45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def render_hops(hops, s):
    rows = [[Paragraph("#", s["TH"]), Paragraph("IP / HOST", s["TH"]),
             Paragraph("LOCATION", s["TH"]), Paragraph("ISP / ASN", s["TH"]),
             Paragraph("STATUS", s["TH"])]]
    for i, hop in enumerate(hops, 1):
        flagged = bool(
            hop.get("flagged")
            or hop.get("suspicious_flags")
            or (hop.get("blacklist") or {}).get("listed")
        )
        fg, bg, status = (
            (RED, RED_SOFT, "FLAGGED") if flagged
            else (MUTED, LIGHT, "INTERNAL") if hop.get("internal")
            else (GREEN, GREEN_SOFT, "OK")
        )
        host = hop.get("reverse") or hop.get("hostname") or "—"
        loc = hop.get("city") or "—"
        if hop.get("country"):
            loc = f"{loc} / {hop['country']}" if hop.get("city") else str(hop["country"])
        rows.append([
            P(i, s, "TB"),
            Paragraph(f"<b>{esc(hop.get('ip') or 'Internal')}</b><br/>{esc(host)}", s["TB"]),
            P(loc, s, "TB"),
            Paragraph(f"{esc(hop.get('isp') or '—')}<br/>ASN {esc(hop.get('asn') or '—')}", s["TB"]),
            badge(status, fg, bg, s, 22 * mm),
        ])
    t = Table(rows, colWidths=[10 * mm, 46 * mm, 40 * mm, 54 * mm, 30 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY),
        ("LINEBELOW", (0, 1), (-1, -1), 0.45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def render_trace(hops, s):
    public = [h for h in hops if h.get("ip") and not h.get("internal")]
    if len(public) < 2:
        return kv([("TraceMap", "Insufficient geolocated public hops for a route diagram.")], s, ORANGE)

    cells = []
    for idx, hop in enumerate(public):
        flagged = bool(
            hop.get("flagged")
            or hop.get("suspicious_flags")
            or (hop.get("blacklist") or {}).get("listed")
        )
        fg, bg = (RED, RED_SOFT) if flagged else (BLUE, LIGHT_BLUE)
        label = hop.get("city") or hop.get("country") or "Unknown"
        ip = hop.get("ip") or "—"
        box = Table([[
            Paragraph(
                f'<font color="{fg.hexval()}"><b>●</b></font><br/>'
                f'<font size="6"><b>{esc(ip)}</b></font><br/>'
                f'<font size="6">{esc(label)}</font>',
                s["Center"]
            )
        ]], colWidths=[30 * mm])
        box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 0.6, fg),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        cells.append(box)
        if idx < len(public) - 1:
            cells.append(Paragraph('<font size="13">→</font>', s["Center"]))

    t = Table([cells], colWidths=[
        30 * mm if i % 2 == 0 else 8 * mm for i in range(len(cells))
    ])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def render_urls(urls, dashboard, s):
    suspicious = int(((dashboard.get("metrics") or {}).get("suspiciousUrlCount") or 0))
    if not urls:
        return kv([("Extracted URLs", "None detected.")], s, CYAN)

    rows = [[Paragraph("URL", s["TH"]), Paragraph("STATUS", s["TH"]),
             Paragraph("RESULT", s["TH"])]]
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
            fg, bg, status = RED, RED_SOFT, "SUSPICIOUS"
            result = reason or "Flagged by the stored case analysis."
        else:
            fg, bg, status = GREEN, GREEN_SOFT, "EXTRACTED"
            result = reason or "Extracted from the email; no per-URL reputation result is stored in this case."
        rows.append([
            P(f"{i}. {url}", s, "TB"),
            badge(status, fg, bg, s, 27 * mm),
            P(result, s, "TB"),
        ])
    t = Table(rows, colWidths=[86 * mm, 31 * mm, 63 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY),
        ("LINEBELOW", (0, 1), (-1, -1), 0.45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def render_attachments(items, s):
    if not items:
        return kv([("Attachments", "None detected.")], s, ORANGE)

    rows = [[Paragraph("FILE", s["TH"]), Paragraph("TYPE / SIZE", s["TH"]),
             Paragraph("RESULT", s["TH"])]]
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("filename") or "Unnamed attachment"
        ext = item.get("extension") or "—"
        size = item.get("size")
        suspicious = bool(item.get("suspicious"))
        reason = item.get("reason") or (
            "Flagged by the parser." if suspicious else "No parser-level issue recorded."
        )
        fg, bg, status = (
            (RED, RED_SOFT, "SUSPICIOUS") if suspicious
            else (GREEN, GREEN_SOFT, "NO FLAG")
        )
        rows.append([
            P(name, s, "TB"),
            Paragraph(f"{esc(ext)}<br/>{esc(str(size) if size is not None else '—')} bytes", s["TB"]),
            Paragraph(
                f'<font color="{fg.hexval()}"><b>{esc(status)}</b></font><br/>{esc(reason)}',
                s["TB"]
            ),
        ])
    t = Table(rows, colWidths=[65 * mm, 39 * mm, 76 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY),
        ("LINEBELOW", (0, 1), (-1, -1), 0.45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


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


def draw_header_footer(canvas, document):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 24 * mm, w, 24 * mm, fill=1, stroke=0)
    canvas.setFillColor(RED)
    canvas.rect(0, h - 24 * mm, 5 * mm, 24 * mm, fill=1, stroke=0)
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, w, 13 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(18 * mm, h - 10 * mm, "MailGuard")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#C9D2E1"))
    canvas.drawString(18 * mm, h - 16 * mm, "EMAIL THREAT DETECTION  •  SECURITY REPORT")
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(18 * mm, 5.2 * mm, "MailGuard  /  REPORT GENERATION")
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(192 * mm, 5.2 * mm, f"PAGE {document.page}")
    canvas.restoreState()


def build_case_pdf(case: dict) -> bytes:
    s = styles()
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=31 * mm, bottomMargin=18 * mm,
        title="MailGuard Security Report",
        author="MailGuard",
        subject="Email Threat Detection and Forensic Intelligence Report",
    )

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
    findings = collect_findings(case, trace)
    action, action_fg, action_bg, action_text = recommendation(score, findings)
    summary = ai.get("summary") or (
        f"MailGuard assigned a risk score of {score}/100. "
        f"The message contains {len(findings)} recorded security finding(s), "
        f"{len(urls)} extracted URL(s), and {len(attachments)} attachment(s)."
    )

    story = [Spacer(1, 3 * mm)]

    # Header
    header = Table([[
        [
            Paragraph('<font color="#DC2626" size="8"><b>CONFIDENTIAL</b></font>', s["Small"]),
            Spacer(1, 1.5 * mm),
            Paragraph("MAILGUARD", s["ReportTitle"]),
            Paragraph("SECURITY REPORT", s["ReportTitle"]),
        ],
        [
            Paragraph("CASE", s["Label"]),
            Paragraph(f"<b>{esc(case_id)}</b>", s["Body"]),
            Spacer(1, 1.5 * mm),
            Paragraph("DATE", s["Label"]),
            Paragraph(esc(format_date(analyzed_at)), s["Value"]),
            Spacer(1, 1.5 * mm),
            Paragraph("VERDICT", s["Label"]),
            badge(verdict, fg, bg, s, 44 * mm),
        ],
    ]], colWidths=[113 * mm, 67 * mm])
    header.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("LINEBEFORE", (0, 0), (0, 0), 4, RED),
        ("BACKGROUND", (1, 0), (1, 0), LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story += [header, Spacer(1, 5 * mm)]

    # Risk score
    risk = Table([[
        Paragraph("RISK SCORE", s["Label"]),
        Paragraph(
            f'<font color="{fg.hexval()}" size="24"><b>{esc(score)}</b></font>'
            '<font color="#687386" size="9"> / 100</font>',
            s["Body"],
        ),
    ]], colWidths=[45 * mm, 135 * mm])
    risk.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [risk, Spacer(1, 7 * mm)]

    # 1. Executive Summary
    story += [section_heading("01", "EXECUTIVE SUMMARY", s, BLUE)]
    summary_box = Table([[Paragraph(esc(summary), s["Body"])]], colWidths=[180 * mm])
    summary_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#C9D8F7")),
        ("LINEBEFORE", (0, 0), (0, -1), 4, BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story += [summary_box, Spacer(1, 6 * mm)]

    # 2. Email Information
    story += [section_heading("02", "EMAIL INFORMATION", s, CYAN)]
    story += [kv([
        ("From", metadata.get("from") or ""),
        ("To", metadata.get("to") or ""),
        ("Reply-To", metadata.get("reply_to") or ""),
        ("Subject", metadata.get("subject") or ""),
        ("Date", metadata.get("date") or ""),
        ("Message-ID", metadata.get("message_id") or ""),
        ("Return-Path", metadata.get("return_path") or ""),
    ], s, CYAN), Spacer(1, 6 * mm)]

    # 3. Authentication
    story += [section_heading("03", "AUTHENTICATION", s, GREEN)]
    auth_rows = [[Paragraph("CHECK", s["TH"]), Paragraph("RESULT", s["TH"]),
                  Paragraph("ASSESSMENT", s["TH"])]]
    for name, value, assessment in [
        ("SPF", checks.get("spf", "none"), "Sender authorization result."),
        ("DKIM", checks.get("dkim", "none"), "Message signature verification."),
        ("DMARC", checks.get("dmarc", "none"), "Domain authentication / alignment."),
        ("Domain",
         "MISMATCH" if checks.get("senderDomainMismatch") else "MATCH",
         "From-domain vs. Reply-To domain."),
    ]:
        auth_rows.append([
            P(name, s, "TB"),
            auth_badge(value, s) if name != "Domain" else (
                badge("MISMATCH", RED, RED_SOFT, s, 27 * mm)
                if checks.get("senderDomainMismatch")
                else badge("MATCH", GREEN, GREEN_SOFT, s, 27 * mm)
            ),
            P(assessment, s, "TB"),
        ])
    auth_table = Table(auth_rows, colWidths=[44 * mm, 36 * mm, 100 * mm], repeatRows=1)
    auth_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [auth_table, Spacer(1, 6 * mm)]

    # 4. Origin & Route Analysis
    story += [section_heading("04", "ORIGIN & ROUTE ANALYSIS", s, ORANGE)]
    first_public = next(
        (h for h in trace.get("hops") or [] if h.get("ip") and not h.get("internal")),
        None,
    )
    first_blacklist = (first_public or {}).get("blacklist") or {}
    abuse = first_blacklist.get("abuse_score")
    if abuse is None:
        abuse = origin.get("abuse_score")
    story += [kv([
        ("Origin IP", origin.get("ip") or "Not identified"),
        ("Location", f"{origin.get('city') or '—'} / {origin.get('country') or '—'}"),
        ("ISP", origin.get("isp") or "—"),
        ("ASN", origin.get("asn") or "—"),
        ("rDNS", origin.get("reverse") or origin.get("hostname") or "—"),
        ("Hosting/VPN", "YES" if origin.get("hosting") or origin.get("proxy") or origin.get("isVpnOrHosting") else "NO"),
        ("Blacklist", "LISTED" if origin.get("blacklisted") or first_blacklist.get("listed") else "NOT LISTED"),
        ("Abuse score", abuse if abuse is not None else "—"),
    ], s, ORANGE)]
    hops = trace.get("hops") or []
    if hops:
        story += [Spacer(1, 4 * mm), Paragraph("RECEIVED HOP TABLE", s["Label"]),
                  render_hops(hops, s), Spacer(1, 4 * mm),
                  Paragraph("TRACEMAP — ROUTE", s["Label"]),
                  render_trace(hops, s)]
    else:
        story += [Spacer(1, 4 * mm), kv([("Received route", "No public Received-chain hops were available.")], s, ORANGE)]
    story += [Spacer(1, 6 * mm)]

    # 5. Security Findings
    story += [section_heading("05", "SECURITY FINDINGS", s, RED),
              render_findings(findings, s), Spacer(1, 6 * mm)]

    # 6. URL Analysis
    story += [section_heading("06", "URL ANALYSIS", s, CYAN),
              render_urls(urls, dashboard, s), Spacer(1, 6 * mm)]

    # 7. Attachments
    story += [section_heading("07", "ATTACHMENTS", s, ORANGE),
              render_attachments(attachments, s), Spacer(1, 6 * mm)]

    # 8. AI / Analyst Explanation
    story += [section_heading("08", "AI / ANALYST EXPLANATION", s, PURPLE)]
    exp = Table([[Paragraph(esc(ai.get("summary") or summary), s["Body"])]], colWidths=[180 * mm])
    exp.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_PURPLE),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D9C9FF")),
        ("LINEBEFORE", (0, 0), (0, -1), 4, PURPLE),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
    ]))
    story += [exp, Spacer(1, 6 * mm)]

    # 9. Recommended Action
    story += [section_heading("09", "RECOMMENDED ACTION", s, action_fg)]
    action_box = Table([[
        badge(action, action_fg, action_bg, s, 55 * mm),
        Paragraph(esc(action_text), s["Body"]),
    ]], colWidths=[60 * mm, 120 * mm])
    action_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), action_bg),
        ("BOX", (0, 0), (-1, -1), 0.7, action_fg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story += [action_box, Spacer(1, 6 * mm)]

    # 10. Forensic / Audit Data
    story += [section_heading("10", "FORENSIC / AUDIT DATA", s, NAVY),
              kv([
                  ("Case ID", case_id),
                  ("Related Cases", len(related)),
                  ("Case Hash", case_hash or "—"),
                  ("Previous Hash", previous_hash or "—"),
                  ("Analysis Timestamp", format_date(analyzed_at)),
                  ("Received Hop Count", len(hops)),
                  ("Finding Count", len(findings)),
                  ("URL Count", len(urls)),
                  ("Attachment Count", len(attachments)),
              ], s, NAVY),
              Spacer(1, 4 * mm),
              Paragraph(
                  "Security note: email-derived values are rendered as escaped text. "
                  "IP geolocation is approximate, and external reputation results may be unavailable "
                  "when they were not stored with the case.",
                  s["Small"]
              )]

    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    buf.seek(0)
    return buf.read()
