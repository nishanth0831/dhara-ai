import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_portfolio_report(applications: list[dict]) -> str:
    base_dir = os.path.dirname(os.path.dirname(__file__))
    out_dir = os.path.join(base_dir, "data", "reports")
    os.makedirs(out_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"DharaAI_Portfolio_Report_{ts}.pdf")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DharaTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=10,
    )
    body_style = ParagraphStyle(
        "DharaBody",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#111827"),
    )
    h_style = ParagraphStyle(
        "DharaHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=8,
        spaceAfter=6,
    )

    total = len(applications)
    total_requested = sum(float(a.get("loan_amount") or 0) for a in applications)
    total_approved = sum(float(a.get("approved_amount") or 0) for a in applications if a.get("status") == "Approved")
    approval_rate = (sum(1 for a in applications if a.get("status") == "Approved") / total * 100.0) if total else 0.0

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        rightMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        topMargin=1.3 * cm,
        bottomMargin=1.3 * cm,
        title="Dhara AI Portfolio Report",
    )

    story = []
    story.append(Paragraph("Dhara AI — Lender Portfolio Report", title_style))
    story.append(Paragraph(f"Generated on <b>{datetime.now().strftime('%d %b %Y, %H:%M')}</b>", body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Portfolio summary", h_style))
    summary = Table(
        [
            ["Applications", str(total)],
            ["Approval rate", f"{approval_rate:.1f}%"],
            ["Total requested", f"₹{int(total_requested):,}"],
            ["Total approved", f"₹{int(total_approved):,}"],
        ],
        colWidths=[5.0 * cm, 12.0 * cm],
    )
    summary.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(summary)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Applications (latest first)", h_style))
    rows = [["ID", "Farmer", "District", "Crop", "Loan (₹)", "Approved (₹)", "Trust", "Conf", "Status"]]
    apps_sorted = sorted(applications, key=lambda a: (a.get("applied_at") or ""), reverse=True)
    for a in apps_sorted[:35]:
        rows.append(
            [
                str(a.get("id", "")),
                str(a.get("farmer_name", ""))[:18],
                str(a.get("district", ""))[:14],
                str(a.get("crop_name", ""))[:12],
                f"{int(float(a.get('loan_amount') or 0)):,}",
                f"{int(float(a.get('approved_amount') or 0)):,}" if a.get("approved_amount") is not None else "-",
                f"{float(a.get('trust_score') or 0):.1f}",
                f"{float(a.get('conf_score') or 0):.1f}",
                str(a.get("status", "")),
            ]
        )

    table = Table(rows, repeatRows=1, colWidths=[1.0 * cm, 3.4 * cm, 2.3 * cm, 2.2 * cm, 2.0 * cm, 2.2 * cm, 1.6 * cm, 1.6 * cm, 2.0 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eff6ff")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)

    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Note: This portfolio report is generated from session applications and is intended for underwriting review and lender briefing.",
            ParagraphStyle("Note", parent=body_style, textColor=colors.HexColor("#475569"), fontSize=9.0),
        )
    )

    doc.build(story)
    return out_path

