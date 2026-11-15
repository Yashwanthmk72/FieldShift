# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Server-side report generation (PDF via reportlab, imported lazily). Includes assumptions and provenance."""
from __future__ import annotations

import io
from typing import Any

from .engine import finance


def _fmt(v: Any) -> str:
    return "n/a" if v is None else (f"{v:,.2f}" if isinstance(v, float) else str(v))


def plan_rows(plans: list[dict[str, Any]], crop_names: dict[str, str]) -> list[dict[str, Any]]:
    rows = []
    for p in plans:
        r = finance.evaluate(p.get("yield_t_ha"), p.get("price_per_t"), {k: p.get("costs", {}).get(k) for k in finance.COST_CATEGORIES}, p.get("area_ha", 1.0))
        prov = p.get("provenance", {})
        rows.append({"crop": crop_names.get(p["crop_id"], p["crop_id"]), "area_ha": p.get("area_ha"), "yield_t_ha": p.get("yield_t_ha"), "price_per_t": p.get("price_per_t"),
                     "cost_total_per_ha": r["cost_total_per_ha"], "revenue_per_ha": r["revenue_per_ha"], "gross_margin_per_ha": r["gross_margin_per_ha"], "net_profit_per_ha": r["net_profit_per_ha"],
                     "break_even_price_per_t": r["break_even_price_per_t"], "break_even_yield_t_ha": r["break_even_yield_t_ha"], "roi": r["roi"],
                     "provenance": "; ".join(f"{k}: {v}" for k, v in sorted(prov.items())) or "not recorded"})
    return rows


def pdf_report(plans: list[dict[str, Any]], crop_names: dict[str, str], title: str = "FieldShift financial plan") -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=title)
    st = getSampleStyleSheet()
    flow: list[Any] = [Paragraph(title, st["Title"]), Paragraph(finance.DISCLAIMER + " Figures use the inputs below; prices, yields and costs are user-entered or labelled assumptions, not market data.", st["Normal"]), Spacer(1, 12)]
    for r in plan_rows(plans, crop_names):
        flow.append(Paragraph(r["crop"], st["Heading2"]))
        data = [["Item", "Value"], ["Area (ha)", _fmt(r["area_ha"])], ["Yield (t/ha)", _fmt(r["yield_t_ha"])], ["Price per t", _fmt(r["price_per_t"])], ["Total cost per ha", _fmt(r["cost_total_per_ha"])],
                ["Revenue per ha", _fmt(r["revenue_per_ha"])], ["Gross margin per ha", _fmt(r["gross_margin_per_ha"])], ["Net profit per ha", _fmt(r["net_profit_per_ha"])],
                ["Break-even price per t", _fmt(r["break_even_price_per_t"])], ["Break-even yield t/ha", _fmt(r["break_even_yield_t_ha"])], ["ROI", _fmt(r["roi"])]]
        flow.append(Table(data, colWidths=[200, 200]))
        flow.append(Paragraph("Provenance: " + r["provenance"].replace("&", "&amp;").replace("<", "&lt;"), st["Italic"]))
        flow.append(Spacer(1, 10))
    if not plans:
        flow.append(Paragraph("No plans saved.", st["Normal"]))
    doc.build(flow)
    return buf.getvalue()
