"""
pdf_export.py — وحدة تصدير PDF لنظام NMCC
الإصدار: 1.0

الاستراتيجية:
  - المسار 1 (الافتراضي): HTML + Print CSS
      يُضمِّن مخططات Plotly تفاعلية كـ SVG ثابت داخل HTML
      ويُقدَّم كزر "طباعة/حفظ PDF" من المتصفح مباشرة.
      → الأفضل لأن المتصفح يتعامل مع العربية والمخططات مثالياً.

  - المسار 2 (احتياطي): reportlab
      يبني PDF عبر reportlab بدون مخططات (جداول ونصوص فقط)
      للحالات التي يريد فيها المستخدم ملف PDF جاهزاً للتحميل.

المتطلبات في requirements.txt:
    reportlab
    Pillow
    plotly  (موجودة أصلاً)
"""

import io
import base64
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable, KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


# ──────────────────────────────────────────────────────────
# الأدوات المشتركة
# ──────────────────────────────────────────────────────────

def _fig_to_svg_b64(fig: go.Figure) -> str:
    """
    يحوّل Figure إلى SVG مُشفَّر base64 لتضمينه في HTML.
    يعمل بدون kaleido عبر Plotly's built-in SVG exporter.
    """
    svg_str = fig.to_image(format="svg").decode("utf-8")
    return base64.b64encode(svg_str.encode()).decode()


def _fig_to_html_div(fig: go.Figure, height: int = 350) -> str:
    """
    يُحوِّل Figure إلى <div> HTML تفاعلي (يعمل في المتصفح فقط).
    يستخدم plotly CDN — لا يحتاج أي مكتبة إضافية.
    """
    return fig.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        config={"displayModeBar": False},
        default_height=height,
    )


def _df_to_html_table(df: pd.DataFrame, rtl: bool = True) -> str:
    """يحوّل DataFrame إلى جدول HTML مُنسَّق."""
    dir_attr = 'dir="rtl"' if rtl else ''
    html  = f'<table {dir_attr} class="data-table">'
    html += "<thead><tr>"
    for col in df.columns:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr>"
        for val in row:
            html += f"<td>{val}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html


# ──────────────────────────────────────────────────────────
# المسار 1: HTML → طباعة من المتصفح
# ──────────────────────────────────────────────────────────

def build_html_report(
    title: str,
    subtitle: str,
    sections: list,          # قائمة من dict: {"title", "type", "content"}
    logo_b64: str = None,
) -> str:
    """
    يبني HTML كاملاً جاهزاً للطباعة كـ PDF من المتصفح.

    sections هي قائمة من العناصر، كل عنصر dict بهذه المفاتيح:
      - title  : str  — عنوان القسم
      - type   : "chart" | "table" | "text" | "kpi_cards" | "divider"
      - content:
          * "chart"     → go.Figure
          * "table"     → pd.DataFrame
          * "text"      → str (HTML مسموح)
          * "kpi_cards" → list of {"label", "value", "color"}
          * "divider"   → None

    مثال:
        sections = [
            {"title": "مؤشرات الأداء", "type": "chart",  "content": fig},
            {"title": "البيانات",       "type": "table",  "content": df},
            {"title": "ملاحظات",        "type": "text",   "content": "النص هنا"},
        ]
    """
    now = datetime.now().strftime("%Y-%m-%d  %H:%M")

    logo_html = ""
    if logo_b64:
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" class="logo" alt="logo">'

    # بناء محتوى الأقسام
    body_html = ""
    for sec in sections:
        sec_type    = sec.get("type", "text")
        sec_title   = sec.get("title", "")
        sec_content = sec.get("content")

        if sec_type == "divider":
            body_html += "<hr class='sec-divider'>"
            continue

        if sec_title:
            body_html += f"<h2 class='sec-title'>{sec_title}</h2>"

        if sec_type == "chart" and sec_content is not None:
            # تضمين المخطط كـ div تفاعلي
            body_html += '<div class="chart-wrap no-break">'
            body_html += _fig_to_html_div(sec_content, height=320)
            body_html += "</div>"

        elif sec_type == "table" and sec_content is not None:
            df = sec_content
            body_html += '<div class="table-wrap">'
            body_html += _df_to_html_table(df)
            body_html += "</div>"

        elif sec_type == "text":
            body_html += f'<div class="text-block">{sec_content}</div>'

        elif sec_type == "kpi_cards" and sec_content:
            body_html += '<div class="kpi-grid">'
            for card in sec_content:
                color = card.get("color", "#0068c9")
                body_html += f"""
                <div class="kpi-card" style="border-top: 4px solid {color}">
                  <div class="kpi-val" style="color:{color}">{card['value']}</div>
                  <div class="kpi-lbl">{card['label']}</div>
                </div>"""
            body_html += "</div>"

    # HTML الكامل
    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  /* ── خط عربي من Google Fonts ── */
  @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap');

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Tajawal', Arial, sans-serif;
    direction: rtl;
    color: #1a1a2e;
    background: #fff;
    font-size: 13px;
    line-height: 1.6;
  }}

  /* ── صفحة الطباعة ── */
  @page {{
    size: A4;
    margin: 1.5cm 1.5cm 2cm 1.5cm;
  }}
  @media print {{
    .no-print {{ display: none !important; }}
    .page-break {{ page-break-before: always; }}
    .no-break   {{ page-break-inside: avoid; }}
    body {{ font-size: 11px; }}
    .chart-wrap .plotly-graph-div {{ height: 280px !important; }}
  }}

  /* ── رأس الصفحة ── */
  .report-header {{
    background: linear-gradient(135deg, #1a237e 0%, #0068c9 100%);
    color: white;
    padding: 28px 32px 22px;
    margin-bottom: 24px;
    border-radius: 0 0 12px 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .header-text h1 {{
    font-size: 22px;
    font-weight: 900;
    margin-bottom: 4px;
  }}
  .header-text .sub {{
    font-size: 13px;
    opacity: .85;
  }}
  .header-meta {{
    text-align: left;
    font-size: 12px;
    opacity: .8;
  }}
  .logo {{
    height: 54px;
    margin-left: 20px;
  }}

  /* ── محتوى ── */
  .content {{ padding: 0 24px 40px; }}

  .sec-title {{
    font-size: 16px;
    font-weight: 700;
    color: #1a237e;
    margin: 22px 0 10px;
    padding-bottom: 6px;
    border-bottom: 2px solid #e8ecf5;
  }}

  .sec-divider {{
    border: none;
    border-top: 1px dashed #d0d5e8;
    margin: 20px 0;
  }}

  /* ── بطاقات KPI ── */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 20px;
  }}
  .kpi-card {{
    background: #f7f9ff;
    border-radius: 10px;
    padding: 14px;
    text-align: center;
    border: 1px solid #e4e9f5;
  }}
  .kpi-val {{
    font-size: 26px;
    font-weight: 900;
    line-height: 1.1;
  }}
  .kpi-lbl {{
    font-size: 12px;
    color: #555;
    margin-top: 4px;
  }}

  /* ── مخططات ── */
  .chart-wrap {{
    background: #fff;
    border-radius: 10px;
    border: 1px solid #e4e9f5;
    padding: 12px;
    margin-bottom: 16px;
    overflow: hidden;
  }}

  /* ── جداول ── */
  .table-wrap {{
    margin-bottom: 16px;
    overflow-x: auto;
  }}
  .data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }}
  .data-table thead tr {{
    background: #1a237e;
    color: white;
  }}
  .data-table th {{
    padding: 9px 12px;
    text-align: right;
    font-weight: 600;
    font-size: 12px;
  }}
  .data-table tbody tr:nth-child(even) {{ background: #f5f7ff; }}
  .data-table tbody tr:hover {{ background: #ebf0ff; }}
  .data-table td {{
    padding: 8px 12px;
    border-bottom: 1px solid #e8ecf5;
    text-align: right;
  }}

  /* ── نص ── */
  .text-block {{
    background: #f7f9ff;
    border-right: 4px solid #0068c9;
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 14px;
    font-size: 13px;
    line-height: 1.7;
  }}

  /* ── تذييل ── */
  .report-footer {{
    margin-top: 32px;
    padding: 14px 24px;
    background: #f5f7ff;
    border-top: 2px solid #e4e9f5;
    border-radius: 8px;
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: #666;
  }}

  /* ── زر الطباعة (يختفي عند الطباعة) ── */
  .print-bar {{
    position: sticky;
    top: 0;
    z-index: 999;
    background: #1a237e;
    padding: 10px 24px;
    display: flex;
    gap: 12px;
    align-items: center;
    box-shadow: 0 2px 8px rgba(0,0,0,.2);
  }}
  .btn-print {{
    background: #fff;
    color: #1a237e;
    border: none;
    padding: 8px 22px;
    border-radius: 6px;
    font-family: 'Tajawal', sans-serif;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    transition: background .2s;
  }}
  .btn-print:hover {{ background: #e8eeff; }}
  .print-hint {{ color: rgba(255,255,255,.75); font-size: 12px; }}
</style>
</head>
<body>

<!-- شريط الطباعة -->
<div class="print-bar no-print">
  <button class="btn-print" onclick="window.print()">🖨️ طباعة / حفظ PDF</button>
  <span class="print-hint">
    عند فتح نافذة الطباعة: اختر "حفظ كـ PDF" أو "Microsoft Print to PDF"
    ← تأكد من تفعيل "الخلفيات والرسوميات" في الإعدادات المتقدمة
  </span>
</div>

<!-- رأس التقرير -->
<div class="report-header">
  <div style="display:flex; align-items:center; gap:16px">
    {logo_html}
    <div class="header-text">
      <h1>{title}</h1>
      <div class="sub">{subtitle}</div>
    </div>
  </div>
  <div class="header-meta">
    <div>📅 {now}</div>
    <div style="margin-top:4px">المركز الوطني للقياس والمعايرة</div>
  </div>
</div>

<!-- المحتوى -->
<div class="content">
{body_html}
</div>

<!-- تذييل -->
<div class="content">
  <div class="report-footer">
    <span>نظام إدارة الاستراتيجية — NMCC 2026</span>
    <span>تاريخ الإصدار: {now}</span>
    <span>نسخة: 34.0</span>
  </div>
</div>

</body>
</html>"""
    return html


def show_html_export_button(
    button_label: str,
    html_content: str,
    filename: str = "report.html",
):
    """
    يعرض زر تحميل HTML في Streamlit.
    المستخدم يفتح الملف في المتصفح ثم يطبعه كـ PDF.
    """
    b64 = base64.b64encode(html_content.encode("utf-8")).decode()
    href = f'data:text/html;base64,{b64}'
    st.markdown(
        f"""
        <a href="{href}" download="{filename}" style="text-decoration:none">
          <button style="
            background:#1a237e; color:white; border:none;
            padding:10px 24px; border-radius:8px; font-family:'Tajawal',sans-serif;
            font-size:15px; font-weight:bold; cursor:pointer; width:100%;
            transition: background 0.2s;
          ">⬇️ {button_label}</button>
        </a>
        <p style="font-size:12px; color:#666; margin-top:6px; direction:rtl">
          افتح الملف في المتصفح ← اضغط زر "🖨️ طباعة / حفظ PDF" داخله
        </p>
        """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────
# المسار 2: reportlab — PDF مباشر (بدون مخططات)
# ──────────────────────────────────────────────────────────

def _rl_styles():
    """ينشئ أنماط reportlab مع دعم نص إنجليزي/أرقام للعربية."""
    styles = getSampleStyleSheet()

    # نمط العنوان الرئيسي
    styles.add(ParagraphStyle(
        name="ArabicTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.HexColor("#1a237e"),
        alignment=TA_CENTER,
        spaceAfter=6,
    ))
    # عنوان قسم
    styles.add(ParagraphStyle(
        name="SectionHead",
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#1a237e"),
        alignment=TA_RIGHT,
        spaceBefore=14,
        spaceAfter=6,
        borderPadding=(0, 0, 4, 0),
    ))
    # نص عادي
    styles.add(ParagraphStyle(
        name="ArabicBody",
        fontName="Helvetica",
        fontSize=10,
        alignment=TA_RIGHT,
        spaceAfter=4,
        leading=16,
    ))
    # تعليق صغير
    styles.add(ParagraphStyle(
        name="Caption",
        fontName="Helvetica",
        fontSize=8,
        textColor=colors.HexColor("#888888"),
        alignment=TA_CENTER,
        spaceAfter=4,
    ))
    return styles


def _rl_table(data: list, col_widths: list = None,
              header_color=None, zebra: bool = True) -> Table:
    """
    يبني Table من reportlab مع تنسيق احترافي.
    data[0] = صف الترويسة، data[1:] = البيانات.
    """
    if header_color is None:
        header_color = colors.HexColor("#1a237e")

    tbl = Table(data, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        # رأس الجدول
        ("BACKGROUND",  (0,0), (-1,0),  header_color),
        ("TEXTCOLOR",   (0,0), (-1,0),  colors.white),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,0),  9),
        ("ALIGN",       (0,0), (-1,0),  "CENTER"),
        ("TOPPADDING",  (0,0), (-1,0),  6),
        ("BOTTOMPADDING",(0,0),(-1,0),  6),
        # بيانات
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,1), (-1,-1), 8),
        ("ALIGN",       (0,1), (-1,-1), "CENTER"),
        ("TOPPADDING",  (0,1), (-1,-1), 4),
        ("BOTTOMPADDING",(0,1),(-1,-1), 4),
        # شبكة
        ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#d0d5e8")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),
         [colors.white, colors.HexColor("#f5f7ff")] if zebra else [colors.white]),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
    ]
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def build_pdf_report(
    title: str,
    subtitle: str,
    kpi_summary: dict,          # {"مبادرات": 12, "أنشطة": 45, ...}
    df_kpis: pd.DataFrame,      # جدول المؤشرات
    df_delayed: pd.DataFrame,   # الأنشطة المتأخرة
    generated_by: str = "النظام",
) -> bytes:
    """
    يبني PDF كاملاً باستخدام reportlab.
    لا يتضمن مخططات (بسبب قيود المكتبة بدون kaleido).
    يُستخدم كملف احتياطي أو للأرشفة.

    يُرجع bytes جاهزة للتحميل بـ st.download_button.
    """
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title=title,
        author="NMCC Strategy System",
    )
    styles = _rl_styles()
    story  = []
    now    = datetime.now().strftime("%Y-%m-%d %H:%M")
    page_w = A4[0] - 4*cm   # عرض المحتوى

    # ── غلاف / رأس ──
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(title, styles["ArabicTitle"]))
    story.append(Paragraph(subtitle, styles["Caption"]))
    story.append(Paragraph(f"تاريخ الإصدار: {now}  |  بواسطة: {generated_by}", styles["Caption"]))
    story.append(HRFlowable(width="100%", thickness=2,
                             color=colors.HexColor("#1a237e"), spaceAfter=12))

    # ── بطاقات الملخص ──
    if kpi_summary:
        story.append(Paragraph("ملخص تنفيذي", styles["SectionHead"]))
        cards_data = [[str(k) for k in kpi_summary.keys()],
                      [str(v) for v in kpi_summary.values()]]
        cw = [page_w / len(kpi_summary)] * len(kpi_summary)
        story.append(_rl_table(cards_data, col_widths=cw))
        story.append(Spacer(1, 0.3*cm))

    # ── جدول المؤشرات ──
    if df_kpis is not None and not df_kpis.empty:
        story.append(Paragraph("مؤشرات الأداء الرئيسية", styles["SectionHead"]))

        # اختر الأعمدة المهمة فقط
        cols_to_show = [c for c in ["KPI_Name","Target","Actual","Unit","Direction","Owner"]
                        if c in df_kpis.columns]
        col_labels   = {"KPI_Name":"المؤشر","Target":"المستهدف","Actual":"المتحقق",
                        "Unit":"الوحدة","Direction":"الاتجاه","Owner":"المسؤول"}
        df_show = df_kpis[cols_to_show].copy()

        header = [col_labels.get(c, c) for c in cols_to_show]
        rows   = [header]
        for _, r in df_show.iterrows():
            row = []
            for c in cols_to_show:
                v = r[c]
                # اجعل الأرقام مقروءة
                if c in ("Target","Actual"):
                    try: v = f"{float(v):.1f}"
                    except: pass
                row.append(str(v)[:40])   # اقطع النص الطويل
            rows.append(row)

        # عرض الأعمدة
        name_w = 5.5*cm
        other_w = (page_w - name_w) / max(len(cols_to_show)-1, 1)
        cw = [name_w] + [other_w]*(len(cols_to_show)-1)
        story.append(_rl_table(rows, col_widths=cw))
        story.append(Spacer(1, 0.3*cm))

    # ── الأنشطة المتأخرة ──
    if df_delayed is not None and not df_delayed.empty:
        story.append(Paragraph(
            f"الأنشطة المتأخرة ({len(df_delayed)})",
            styles["SectionHead"]))

        cols2   = [c for c in ["Mabadara","Activity","Progress","End_Date"]
                   if c in df_delayed.columns]
        labels2 = {"Mabadara":"المبادرة","Activity":"النشاط",
                   "Progress":"الإنجاز%","End_Date":"تاريخ الانتهاء"}
        header2 = [labels2.get(c,c) for c in cols2]
        rows2   = [header2]
        for _, r in df_delayed.iterrows():
            row = []
            for c in cols2:
                v = str(r[c])
                if c in ("Mabadara","Activity") and len(v) > 35:
                    v = v[:33] + "…"
                row.append(v)
            rows2.append(row)

        name_w2 = 3.5*cm; act_w2 = 5*cm; other_w2 = (page_w-name_w2-act_w2)/max(len(cols2)-2,1)
        cw2 = [name_w2, act_w2] + [other_w2]*(len(cols2)-2)
        story.append(_rl_table(rows2, col_widths=cw2,
                               header_color=colors.HexColor("#c0392b")))
        story.append(Spacer(1, 0.3*cm))

    # ── تذييل ──
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1,
                             color=colors.HexColor("#d0d5e8"), spaceAfter=8))
    story.append(Paragraph(
        f"نظام إدارة الاستراتيجية — NMCC 2026  |  الإصدار 34.0  |  {now}",
        styles["Caption"]))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ──────────────────────────────────────────────────────────
# واجهة Streamlit الرئيسية — تُستدعى من admin_view
# ──────────────────────────────────────────────────────────

def show_export_section(
    df_kpi: pd.DataFrame,
    df_acts: pd.DataFrame,
    kpi_figs: dict,            # {"عنوان المخطط": go.Figure, ...}
    user_name: str = "Admin",
):
    """
    يعرض قسم التصدير الكامل داخل لوحة المدير.

    الاستخدام في admin_view():
        from pdf_export import show_export_section
        show_export_section(df_kpi, df_acts, kpi_figs, user_name)

    kpi_figs مثال:
        kpi_figs = {
            "مجموعة QI4SD":            fig_qi4sd,
            "مجموعة البحث والتطوير":   fig_research,
            "مجموعة الكفاءة التشغيلية":fig_ops,
        }
    """
    st.markdown("## 📄 تصدير التقرير")

    # ── إعدادات التقرير ──
    with st.expander("⚙️ خيارات التقرير", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            rpt_title    = st.text_input("عنوان التقرير",
                                          value="تقرير متابعة الأداء الاستراتيجي")
            rpt_subtitle = st.text_input("العنوان الفرعي",
                                          value=f"المركز الوطني للقياس والمعايرة — {datetime.now().strftime('%Y')}")
        with c2:
            include_kpi    = st.checkbox("✅ تضمين جدول المؤشرات",    value=True)
            include_charts = st.checkbox("✅ تضمين المخططات البيانية", value=True)
            include_delay  = st.checkbox("✅ تضمين الأنشطة المتأخرة", value=True)

    st.markdown("---")

    # ── حساب الملخص ──
    today_dt   = __import__('datetime').date.today()
    df_acts_cp = df_acts.copy()
    df_acts_cp['_end'] = __import__('pandas').to_datetime(
        df_acts_cp.get('End_Date',''), errors='coerce').dt.date
    df_acts_cp['Progress'] = df_acts_cp['Progress'].apply(
        lambda x: int(float(str(x).replace('%','') or 0)))

    delayed = df_acts_cp[(df_acts_cp['Progress']<100) &
                         (df_acts_cp['_end'].notna()) &
                         (df_acts_cp['_end'] < today_dt)]
    avg_prog = df_acts_cp['Progress'].mean()

    summary = {
        "المبادرات":      str(df_acts_cp['Mabadara'].nunique()),
        "الأنشطة":        str(len(df_acts_cp)),
        "متوسط الإنجاز":  f"{avg_prog:.1f}%",
        "أنشطة متأخرة":   str(len(delayed)),
        "المؤشرات":       str(len(df_kpi)) if df_kpi is not None else "0",
    }

    # ══════════════════════════════
    # زر 1: تقرير HTML (مع المخططات)
    # ══════════════════════════════
    st.markdown("### 🌐 تقرير HTML (الأفضل — يشمل المخططات التفاعلية)")
    st.caption("ملف HTML يُفتح في المتصفح → اضغط زر الطباعة داخله → احفظ كـ PDF")

    if st.button("🔨 بناء تقرير HTML", type="primary", use_container_width=True,
                 key="build_html"):
        with st.spinner("جاري بناء التقرير..."):
            sections = []

            # بطاقات الملخص
            cards = [
                {"label": k, "value": v,
                 "color": "#e74c3c" if k == "أنشطة متأخرة" else "#0068c9"}
                for k, v in summary.items()
            ]
            sections.append({"title": "الملخص التنفيذي",
                              "type": "kpi_cards", "content": cards})

            # المخططات
            if include_charts and kpi_figs:
                sections.append({"type": "divider"})
                sections.append({"title": "مؤشرات الأداء البيانية", "type": "text",
                                 "content": ""})
                for fig_title, fig in kpi_figs.items():
                    sections.append({"title": fig_title,
                                     "type": "chart", "content": fig})

            # جدول المؤشرات
            if include_kpi and df_kpi is not None and not df_kpi.empty:
                sections.append({"type": "divider"})
                cols_show = [c for c in
                             ["KPI_Name","Target","Actual","Unit","Direction","Owner"]
                             if c in df_kpi.columns]
                lbl_map = {"KPI_Name":"المؤشر","Target":"المستهدف","Actual":"المتحقق",
                           "Unit":"الوحدة","Direction":"الاتجاه","Owner":"المسؤول"}
                df_disp = df_kpi[cols_show].rename(columns=lbl_map)
                sections.append({"title": "جدول مؤشرات الأداء",
                                 "type": "table", "content": df_disp})

            # الأنشطة المتأخرة
            if include_delay and not delayed.empty:
                sections.append({"type": "divider"})
                cols_d = [c for c in ["Mabadara","Activity","Progress","End_Date"]
                          if c in delayed.columns]
                lbl_d  = {"Mabadara":"المبادرة","Activity":"النشاط",
                          "Progress":"الإنجاز %","End_Date":"تاريخ الانتهاء"}
                df_d   = delayed[cols_d].rename(columns=lbl_d).drop(columns=['_end'],errors='ignore')
                sections.append({"title": f"الأنشطة المتأخرة ({len(delayed)})",
                                 "type": "table", "content": df_d})

            html_report = build_html_report(
                title=rpt_title,
                subtitle=rpt_subtitle,
                sections=sections,
            )
            fname = f"NMCC_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
            show_html_export_button("⬇️ تحميل تقرير HTML", html_report, fname)

    st.markdown("---")

    # ══════════════════════════════
    # زر 2: PDF مباشر (بدون مخططات)
    # ══════════════════════════════
    st.markdown("### 📄 تقرير PDF مباشر (جداول فقط — للأرشفة)")
    st.caption("يُنزَّل مباشرة كـ .pdf — لا يحتاج فتح المتصفح — لكن بدون مخططات بيانية")

    if st.button("⬇️ تحميل PDF مباشرة", use_container_width=True, key="build_pdf"):
        with st.spinner("جاري بناء ملف PDF..."):
            df_del_clean = delayed.drop(columns=['_end'], errors='ignore') \
                           if not delayed.empty else delayed
            pdf_bytes = build_pdf_report(
                title=rpt_title,
                subtitle=rpt_subtitle,
                kpi_summary=summary,
                df_kpis=df_kpi,
                df_delayed=df_del_clean,
                generated_by=user_name,
            )
        fname_pdf = f"NMCC_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        st.download_button(
            label="📥 اضغط هنا لتحميل الملف",
            data=pdf_bytes,
            file_name=fname_pdf,
            mime="application/pdf",
            use_container_width=True,
        )
        st.success(f"✅ تم بناء PDF — {len(pdf_bytes)//1024} KB")
