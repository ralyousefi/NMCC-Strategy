import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import re
import time
from datetime import datetime, date

# ---------------------------------------------------------
# 1. إعدادات الصفحة
# ---------------------------------------------------------
st.set_page_config(page_title="نظام إدارة الاستراتيجية", layout="wide", page_icon="📊")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Tajawal', sans-serif; direction: rtl; }
    h1,h2,h3,h4,p,div,input,select,textarea,.stSelectbox,.stNumberInput { text-align: right; }
    .stDataFrame { direction: rtl; }

    div[data-testid="stMetric"] {
        background-color: #ffffff; border: 1px solid #e6e6e6;
        padding: 15px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,.05); text-align: center;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 20px !important; color: #0068c9 !important;
        font-weight: bold !important; justify-content: center;
    }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #0068c9; font-weight: bold; }

    .history-box {
        background: #eef5ff; padding: 15px; border-radius: 8px;
        border: 1px solid #d0e2ff; margin-top: 10px; margin-bottom: 20px;
        font-size: 15px; line-height: 1.6; white-space: pre-wrap;
        box-shadow: inset 0 0 5px rgba(0,0,0,.05);
    }
    .history-title { color: #0068c9; font-weight: bold; margin-bottom: 5px; font-size: 16px; }
    .admin-alert-box {
        background: #fff3cd; color: #856404; padding: 15px; border-radius: 8px;
        border: 1px solid #ffeeba; border-right: 5px solid #ffc107;
        margin-bottom: 20px; font-weight: bold;
    }
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background: #f1f1f1; color: #555; text-align: center;
        padding: 10px; font-size: 12px; border-top: 1px solid #ddd; z-index: 100;
    }

    /* تنبيهات */
    .alert-summary-grid {
        display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin-bottom: 20px;
    }
    .alert-summary-card { border-radius: 10px; padding: 16px; text-align: center; }
    .alert-summary-card .num { font-size: 32px; font-weight: 900; line-height: 1; }
    .alert-summary-card .lbl { font-size: 13px; margin-top: 4px; opacity: .85; }
    .s-red    { background: #fde8e8; color: #c0392b; }
    .s-orange { background: #fef3cd; color: #d35400; }
    .s-blue   { background: #e8f4fd; color: #1a5276; }
    .s-gray   { background: #f3f3f3; color: #2c3e50; }
    .alert-header {
        display: flex; align-items: center; gap: 10px; padding: 14px 18px;
        border-radius: 10px; margin-bottom: 8px; font-weight: bold; direction: rtl;
    }
    .alert-overdue { background: #fde8e8; border-right: 5px solid #c0392b; color: #7b241c; }
    .alert-at-risk { background: #fef3cd; border-right: 5px solid #e67e22; color: #784212; }
    .all-good {
        background: #eafaf1; border-right: 5px solid #27ae60; border-radius: 8px;
        padding: 12px 18px; color: #1e8449; font-weight: bold; margin-bottom: 10px; direction: rtl;
    }

    /* تتبع تاريخي */
    .trend-card {
        background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
        padding: 14px 18px; margin-bottom: 12px;
    }
    .trend-up   { color: #27ae60; font-weight: bold; font-size: 15px; }
    .trend-down { color: #e74c3c; font-weight: bold; font-size: 15px; }
    .trend-flat { color: #f39c12; font-weight: bold; font-size: 15px; }
    .snapshot-info {
        background: #f0f4ff; border-radius: 8px; padding: 10px 16px;
        border-right: 4px solid #3498db; margin-bottom: 12px; font-size: 14px;
    }
    /* محادثة */
    .chat-wrap { display: flex; flex-direction: column; gap: 10px; padding: 12px 4px; direction: rtl; }
    .bubble { max-width: 78%; padding: 10px 14px; border-radius: 16px; font-size: 13.5px;
        line-height: 1.6; word-break: break-word; font-family: 'Tajawal', sans-serif; }
    .bubble-admin { background: #1a237e; color: #fff; align-self: flex-end;
        border-bottom-right-radius: 4px; margin-left: auto; }
    .bubble-admin .meta { font-size: 11px; opacity: .7; margin-bottom: 4px; }
    .bubble-owner { background: #f0f4ff; color: #1a237e; border: 1px solid #dce4ff;
        align-self: flex-start; border-bottom-left-radius: 4px; margin-right: auto; }
    .bubble-owner .meta { font-size: 11px; color: #5c6bc0; margin-bottom: 4px; }
    .chat-empty { text-align: center; color: #aaa; font-size: 13px; padding: 24px 0; direction: rtl; }
    .chat-divider { text-align: center; color: #bbb; font-size: 11px; padding: 4px 0; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. تعريف المجموعات
# ---------------------------------------------------------
KPI_GROUPS = {
    "QI4SD": [
        "QI4SD - Metrology", "CMC", "B of CMC", "ILC", "CC",
        "OIML project groups", "OIML-CS - number of services offered",
    ],
    "البحث والتطوير": [
        "عدد الابحاث العلمية المنشورة في مجلات مصنفة دولياً Q1, Q2",
        "عدد المشاركات العلمية الدولية", "عدد الطلاب الملتحقين",
        "عدد فعاليات الاستقطاب الجامعي", "عدد المشاريع الوطنية",
        "عدد المشاركين سنوياً في برامج التبادل الفني",
    ],
    "الكفاءة التشغيلية": [
        "نسبة نضج الحوكمة المؤسسية KAQA", "مؤشر التميز المؤسسي",
        "نسبة الإجراءات المؤتمتة", "مستوى رضا المستفيدين", "التحول الرقمي DGA",
        "نسبة الدوران الوظيفي", "نسبة الإيرادات الى إجمالي ميزانية",
        "نسبة النمو في إيرادات",
    ],
}

def get_kpi_category(kpi_name):
    kpi_name = str(kpi_name).strip()
    for group, items in KPI_GROUPS.items():
        if kpi_name in [str(i).strip() for i in items]:
            return group
    return "مؤشرات أخرى"

# ---------------------------------------------------------
# 3. اتصال Google Sheets
# ---------------------------------------------------------
SHEET_ID         = "11tKfYa-Sqa96wDwQvMvChgRWaxgMRAWAIvul7p27ayY"
KPI_HISTORY_SHEET = "KPI_History"   # الورقة الجديدة للتاريخ

def get_creds():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    try:
        if st.secrets is not None and 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if 'private_key' in creds_dict:
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
            return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception:
        pass
    if os.path.exists("credentials.json"):
        return ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    st.error("⚠️ خطأ في الاتصال: لم يتم العثور على ملف الاعتمادات أو Secrets.")
    st.stop()

def get_sheet_connection():
    creds  = get_creds()
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

# ---------------------------------------------------------
# 4. دوال مساعدة
# ---------------------------------------------------------
def safe_int(val):
    try:
        if str(val).strip() == '': return 0
        return int(float(str(val).replace('%', '').strip()))
    except: return 0

def safe_float(val):
    try:
        if str(val).strip() == '': return 0.0
        return float(str(val).replace('%', '').strip())
    except: return 0.0

def clean_df_for_gspread(df):
    df_clean = df.fillna("")
    return df_clean.astype(object).where(pd.notnull(df_clean), "")

def parse_date(date_str):
    try: return pd.to_datetime(date_str).date()
    except: return datetime.today().date()

def append_timestamped_comment(original_text, new_comment):
    if not new_comment or str(new_comment).strip() == "":
        return original_text
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = f"📅 {timestamp}: {str(new_comment).strip()}"
    if original_text and str(original_text).strip() != "":
        return f"{str(original_text)}\n----------------\n{new_entry}"
    return new_entry

def _last_update_date(comment_text: str):
    if not comment_text or str(comment_text).strip() == "": return None
    dates = re.findall(r"(\d{4}-\d{2}-\d{2})", str(comment_text))
    if not dates: return None
    try: return datetime.strptime(dates[-1], "%Y-%m-%d").date()
    except: return None

def _parse_end_date(val):
    try: return pd.to_datetime(str(val)).date()
    except: return None

# ---------------------------------------------------------
# 5. ═══════ نظام التتبع التاريخي ═══════
#
#  هيكل ورقة KPI_History (تُنشأ تلقائياً):
#  KPI_Name | Date | Actual | Target | Recorded_By | Note
# ---------------------------------------------------------

@st.cache_data(ttl=120, show_spinner=False)
def load_kpi_history(_cache_key: str) -> pd.DataFrame:
    """
    يحمّل جميع السجلات من ورقة KPI_History.
    يُنشئ الورقة تلقائياً إن لم تكن موجودة.
    مُخزَّن في cache لمدة دقيقتين.
    """
    COLS = ["KPI_Name", "Date", "Actual", "Target", "Recorded_By", "Note"]
    empty = pd.DataFrame(columns=COLS)
    try:
        sh = get_sheet_connection()
        try:
            ws = sh.worksheet(KPI_HISTORY_SHEET)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=KPI_HISTORY_SHEET, rows=2000, cols=6)
            ws.append_row(COLS)
            return empty

        records = ws.get_all_records()
        if not records:
            return empty

        df = pd.DataFrame(records)
        df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
        df["Actual"] = df["Actual"].apply(safe_float)
        df["Target"] = df["Target"].apply(safe_float)
        return df.dropna(subset=["Date"])
    except Exception as e:
        st.warning(f"تحذير: تعذّر تحميل السجل التاريخي — {e}")
        return empty


def _get_or_create_history_ws(sh):
    """يُرجع ورقة KPI_History، وينشئها إن لم تكن موجودة."""
    try:
        return sh.worksheet(KPI_HISTORY_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=KPI_HISTORY_SHEET, rows=2000, cols=6)
        ws.append_row(["KPI_Name", "Date", "Actual", "Target", "Recorded_By", "Note"])
        return ws


def save_kpi_snapshot(kpi_name: str, actual: float, target: float,
                      recorded_by: str, note: str = "") -> bool:
    """
    يحفظ لقطة مؤشر واحد في KPI_History.
    إذا كان اليوم مُسجَّلاً بالفعل → يُحدِّث الصف بدلاً من تكراره.
    يُستدعى تلقائياً من زر "حفظ تحديث المؤشر" في owner_view.
    """
    today_str = date.today().isoformat()
    try:
        sh = get_sheet_connection()
        ws = _get_or_create_history_ws(sh)
        records = ws.get_all_records()

        for i, r in enumerate(records):
            if (str(r.get("KPI_Name","")).strip() == kpi_name.strip()
                    and str(r.get("Date","")).strip() == today_str):
                row_idx = i + 2   # +1 للـ header, +1 لـ 1-based
                ws.update(f"A{row_idx}:F{row_idx}",
                          [[kpi_name, today_str, actual, target, recorded_by, note]])
                load_kpi_history.clear()
                return True

        ws.append_row([kpi_name, today_str, actual, target, recorded_by, note])
        load_kpi_history.clear()
        return True
    except Exception as e:
        st.error(f"خطأ في حفظ السجل التاريخي: {e}")
        return False


def save_all_kpis_snapshot(df_kpi: pd.DataFrame, recorded_by: str) -> int:
    """
    يسجّل لقطة لجميع المؤشرات دفعةً واحدة (batch).
    يُحدِّث الصفوف الموجودة لنفس اليوم ويضيف الجديدة.
    يُرجع عدد السجلات المعالجة.
    """
    today_str = date.today().isoformat()
    try:
        sh = get_sheet_connection()
        ws = _get_or_create_history_ws(sh)
        existing  = ws.get_all_records()
        exist_map = {
            (str(r["KPI_Name"]).strip(), str(r["Date"]).strip()): i + 2
            for i, r in enumerate(existing)
        }
        new_rows   = []
        update_ops = []

        for _, row in df_kpi.iterrows():
            kpi    = str(row.get("KPI_Name", "")).strip()
            actual = safe_float(row.get("Actual", 0))
            target = safe_float(row.get("Target", 0))
            key    = (kpi, today_str)

            if key in exist_map:
                update_ops.append((exist_map[key],
                                   [kpi, today_str, actual, target, recorded_by, "لقطة شاملة"]))
            else:
                new_rows.append([kpi, today_str, actual, target, recorded_by, "لقطة شاملة"])

        for row_idx, data in update_ops:
            ws.update(f"A{row_idx}:F{row_idx}", [data])

        if new_rows:
            ws.append_rows(new_rows, value_input_option="USER_ENTERED")

        load_kpi_history.clear()
        return len(new_rows) + len(update_ops)
    except Exception as e:
        st.error(f"خطأ في اللقطة الشاملة: {e}")
        return 0


# ---------------------------------------------------------
# 6. دوال الرسم والتحليل التاريخي
# ---------------------------------------------------------

def compute_trend(series: pd.Series) -> dict:
    """يحلّل آخر قيمتين ويُرجع الاتجاه والنسبة والأيقونة."""
    vals = series.dropna().tolist()
    if len(vals) < 2:
        return {"direction": "flat", "pct": 0.0,
                "label": "لا يوجد سجل كافٍ", "css": "trend-flat", "icon": "➖"}
    last, prev = vals[-1], vals[-2]
    pct = ((last - prev) / abs(prev) * 100) if prev != 0 else (100.0 if last > 0 else 0.0)
    if   pct >  2: return {"direction":"up",   "pct":pct,  "label":f"▲ {pct:.1f}%",       "css":"trend-up",   "icon":"▲"}
    elif pct < -2: return {"direction":"down",  "pct":pct,  "label":f"▼ {abs(pct):.1f}%",  "css":"trend-down", "icon":"▼"}
    else:          return {"direction":"flat",  "pct":pct,  "label":"مستقر ➖",              "css":"trend-flat", "icon":"➖"}


def plot_kpi_trend(df_history: pd.DataFrame, kpi_name: str,
                   direction: str = "تصاعدي", unit: str = "", ctx: str = ""):
    """
    يرسم رسماً خطياً للاتجاه لمؤشر واحد.
    - خط الفعلي ملوَّن بناءً على الاتجاه
    - خط المستهدف منقّط
    - آخر قيمة مميّزة بنقطة أكبر
    - جدول البيانات قابل للطي
    """
    df = df_history[
        df_history["KPI_Name"].astype(str).str.strip() == kpi_name.strip()
    ].copy().sort_values("Date")

    if df.empty:
        st.info("لا توجد بيانات تاريخية بعد — سجّل أول قيمة باستخدام زر التحديث أو اللقطة الشاملة.")
        return

    trend = compute_trend(df["Actual"])

    # لون الخط حسب الاتجاه والمنطق (تصاعدي/تنازلي)
    if direction == "تنازلي":
        line_color = "#27ae60" if trend["direction"] == "down" else \
                     "#e74c3c" if trend["direction"] == "up"   else "#3498db"
    else:
        line_color = "#27ae60" if trend["direction"] == "up"   else \
                     "#e74c3c" if trend["direction"] == "down" else "#3498db"

    fig = go.Figure()

    # منطقة المستهدف
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Target"],
        mode="lines", name="المستهدف",
        line=dict(color="#e67e22", width=2, dash="dot"),
        hovertemplate="المستهدف: %{y}<extra></extra>"))

    # خط الفعلي
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Actual"],
        mode="lines+markers+text",
        name="الفعلي",
        line=dict(color=line_color, width=3),
        marker=dict(size=8, color=line_color, line=dict(color="white", width=2)),
        text=[f"{v:.1f}" for v in df["Actual"]],
        textposition="top center",
        textfont=dict(size=11, color=line_color),
        hovertemplate="<b>%{x|%Y-%m-%d}</b><br>الفعلي: %{y}<extra></extra>"))

    # نقطة آخر قيمة (مميّزة)
    last = df.iloc[-1]
    fig.add_trace(go.Scatter(
        x=[last["Date"]], y=[last["Actual"]],
        mode="markers", showlegend=False,
        marker=dict(size=15, color=line_color,
                    line=dict(color="white", width=3), symbol="circle"),
        hovertemplate=f"آخر قيمة: {last['Actual']:.1f}<extra></extra>"))

    fig.update_layout(
        title=dict(
            text=f"<b>{kpi_name[:45]}</b>   <span style='color:{line_color}'>{trend['label']}</span>",
            x=0.5, xanchor="center", font=dict(size=13)),
        xaxis=dict(title="", showgrid=True, gridcolor="#f0f0f0", tickformat="%b %Y"),
        yaxis=dict(title=unit or "القيمة", showgrid=True, gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=70, b=30, l=40, r=20), height=300,
        hovermode="x unified")

    safe_key = (kpi_name + ctx).replace(' ','_').replace('/','_').replace('-','_')[:80]
    st.plotly_chart(fig, use_container_width=True, key=f"trend_{safe_key}")

    with st.expander("📋 جدول البيانات التاريخية"):
        show = df[["Date", "Actual", "Target", "Recorded_By", "Note"]].copy()
        show["Date"] = show["Date"].dt.strftime("%Y-%m-%d")
        show.columns = ["التاريخ", "الفعلي", "المستهدف", "سجّل بواسطة", "ملاحظة"]
        st.dataframe(show.sort_values("التاريخ", ascending=False),
                     hide_index=True, use_container_width=True)


def show_history_overview(df_history: pd.DataFrame, df_kpi: pd.DataFrame):
    """نظرة عامة: رسم خطي لكل مجموعة في شبكة 2 عمود."""
    if df_history.empty:
        st.markdown(
            "<div class='snapshot-info'>📌 لا يوجد سجل تاريخي بعد — "
            "اضغط <b>تسجيل لقطة شاملة</b> لبدء التتبع.</div>",
            unsafe_allow_html=True)
        return

    cats = ["الكل"] + list(KPI_GROUPS.keys())
    sel  = st.selectbox("🔍 عرض مجموعة:", cats, key="ov_cat")

    recorded = df_history["KPI_Name"].astype(str).str.strip().unique().tolist()
    if sel == "الكل":
        kpis = recorded
    else:
        kpis = [k for k in KPI_GROUPS.get(sel, []) if k in recorded]

    if not kpis:
        st.info("لا توجد بيانات تاريخية للمجموعة المختارة بعد.")
        return

    cols = st.columns(2)
    for i, kpi in enumerate(kpis):
        kpi_info  = df_kpi[df_kpi["KPI_Name"].astype(str).str.strip() == kpi.strip()]
        unit      = kpi_info["Unit"].values[0]      if not kpi_info.empty and "Unit"      in kpi_info.columns else ""
        direction = kpi_info["Direction"].values[0] if not kpi_info.empty and "Direction" in kpi_info.columns else "تصاعدي"

        kpi_hist = df_history[df_history["KPI_Name"].astype(str).str.strip() == kpi.strip()].sort_values("Date")
        trend    = compute_trend(kpi_hist["Actual"])

        with cols[i % 2]:
            st.markdown(
                f"<div class='trend-card'>"
                f"<b>{kpi[:55]}</b><br>"
                f"<span class='{trend['css']}'>{trend['label']}</span>"
                f" &nbsp;|&nbsp; آخر قيمة: <b>{kpi_hist['Actual'].iloc[-1]:.1f}</b>"
                f"</div>",
                unsafe_allow_html=True)
            plot_kpi_trend(df_history, kpi, direction, unit, ctx="_ov")



# ---------------------------------------------------------
# 5. نظام المحادثة
# ---------------------------------------------------------
_CHAT_ICON = "📅"
_MSG_PATTERN = re.compile(
    r"📅\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})(?:\s*\[(\w+)\])?:\s*(.*?)(?=📅|\Z)",
    re.DOTALL,
)

def _parse_messages(text: str, default_role: str) -> list:
    if not text or str(text).strip() == "": return []
    msgs = []
    for m in _MSG_PATTERN.finditer(str(text)):
        dt_str = m.group(1).strip()
        role   = (m.group(2) or default_role).strip()
        body   = m.group(3).strip().replace("----------------", "").strip()
        if not body: continue
        try: dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        except: dt = datetime.min
        msgs.append({"dt": dt, "role": role, "text": body})
    return msgs

def _merge_and_sort(owner_text: str, admin_text: str) -> list:
    return sorted(
        _parse_messages(owner_text, "Owner") + _parse_messages(        "OIML project groups", "OIML-CS - number of services offered",
    ],
    "البحث والتطوير": [
        "عدد الابحاث العلمية المنشورة في مجلات مصنفة دولياً Q1, Q2",
        "عدد المشاركات العلمية الدولية", "عدد الطلاب الملتحقين",
        "عدد فعاليات الاستقطاب الجامعي", "عدد المشاريع الوطنية",
        "عدد المشاركين سنوياً في برامج التبادل الفني",
    ],
    "الكفاءة التشغيلية": [
        "نسبة نضج الحوكمة المؤسسية KAQA", "مؤشر التميز المؤسسي",
        "نسبة الإجراءات المؤتمتة", "مستوى رضا المستفيدين", "التحول الرقمي DGA",
        "نسبة الدوران الوظيفي", "نسبة الإيرادات الى إجمالي ميزانية",
        "نسبة النمو في إيرادات",
    ],
}

def get_kpi_category(kpi_name):
    kpi_name = str(kpi_name).strip()
    for group, items in KPI_GROUPS.items():
        if kpi_name in [str(i).strip() for i in items]:
            return group
    return "مؤشرات أخرى"

# ---------------------------------------------------------
# 3. اتصال Google Sheets
# ---------------------------------------------------------
SHEET_ID         = "11tKfYa-Sqa96wDwQvMvChgRWaxgMRAWAIvul7p27ayY"
KPI_HISTORY_SHEET = "KPI_History"   # الورقة الجديدة للتاريخ

def get_creds():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    try:
        if st.secrets is not None and 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if 'private_key' in creds_dict:
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
            return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception:
        pass
    if os.path.exists("credentials.json"):
        return ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    st.error("⚠️ خطأ في الاتصال: لم يتم العثور على ملف الاعتمادات أو Secrets.")
    st.stop()

def get_sheet_connection():
    creds  = get_creds()
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

# ---------------------------------------------------------
# 4. دوال مساعدة
# ---------------------------------------------------------
def safe_int(val):
    try:
        if str(val).strip() == '': return 0
        return int(float(str(val).replace('%', '').strip()))
    except: return 0

def safe_float(val):
    try:
        if str(val).strip() == '': return 0.0
        return float(str(val).replace('%', '').strip())
    except: return 0.0

def clean_df_for_gspread(df):
    df_clean = df.fillna("")
    return df_clean.astype(object).where(pd.notnull(df_clean), "")

def parse_date(date_str):
    try: return pd.to_datetime(date_str).date()
    except: return datetime.today().date()

def append_timestamped_comment(original_text, new_comment):
    if not new_comment or str(new_comment).strip() == "":
        return original_text
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = f"📅 {timestamp}: {str(new_comment).strip()}"
    if original_text and str(original_text).strip() != "":
        return f"{str(original_text)}\n----------------\n{new_entry}"
    return new_entry

def _last_update_date(comment_text: str):
    if not comment_text or str(comment_text).strip() == "": return None
    dates = re.findall(r"(\d{4}-\d{2}-\d{2})", str(comment_text))
    if not dates: return None
    try: return datetime.strptime(dates[-1], "%Y-%m-%d").date()
    except: return None

def _parse_end_date(val):
    try: return pd.to_datetime(str(val)).date()
    except: return None

# ---------------------------------------------------------
# 5. ═══════ نظام التتبع التاريخي ═══════
#
#  هيكل ورقة KPI_History (تُنشأ تلقائياً):
#  KPI_Name | Date | Actual | Target | Recorded_By | Note
# ---------------------------------------------------------

@st.cache_data(ttl=120, show_spinner=False)
def load_kpi_history(_cache_key: str) -> pd.DataFrame:
    """
    يحمّل جميع السجلات من ورقة KPI_History.
    يُنشئ الورقة تلقائياً إن لم تكن موجودة.
    مُخزَّن في cache لمدة دقيقتين.
    """
    COLS = ["KPI_Name", "Date", "Actual", "Target", "Recorded_By", "Note"]
    empty = pd.DataFrame(columns=COLS)
    try:
        sh = get_sheet_connection()
        try:
            ws = sh.worksheet(KPI_HISTORY_SHEET)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=KPI_HISTORY_SHEET, rows=2000, cols=6)
            ws.append_row(COLS)
            return empty

        records = ws.get_all_records()
        if not records:
            return empty

        df = pd.DataFrame(records)
        df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
        df["Actual"] = df["Actual"].apply(safe_float)
        df["Target"] = df["Target"].apply(safe_float)
        return df.dropna(subset=["Date"])
    except Exception as e:
        st.warning(f"تحذير: تعذّر تحميل السجل التاريخي — {e}")
        return empty


def _get_or_create_history_ws(sh):
    """يُرجع ورقة KPI_History، وينشئها إن لم تكن موجودة."""
    try:
        return sh.worksheet(KPI_HISTORY_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=KPI_HISTORY_SHEET, rows=2000, cols=6)
        ws.append_row(["KPI_Name", "Date", "Actual", "Target", "Recorded_By", "Note"])
        return ws


def save_kpi_snapshot(kpi_name: str, actual: float, target: float,
                      recorded_by: str, note: str = "") -> bool:
    """
    يحفظ لقطة مؤشر واحد في KPI_History.
    إذا كان اليوم مُسجَّلاً بالفعل → يُحدِّث الصف بدلاً من تكراره.
    يُستدعى تلقائياً من زر "حفظ تحديث المؤشر" في owner_view.
    """
    today_str = date.today().isoformat()
    try:
        sh = get_sheet_connection()
        ws = _get_or_create_history_ws(sh)
        records = ws.get_all_records()

        for i, r in enumerate(records):
            if (str(r.get("KPI_Name","")).strip() == kpi_name.strip()
                    and str(r.get("Date","")).strip() == today_str):
                row_idx = i + 2   # +1 للـ header, +1 لـ 1-based
                ws.update(f"A{row_idx}:F{row_idx}",
                          [[kpi_name, today_str, actual, target, recorded_by, note]])
                load_kpi_history.clear()
                return True

        ws.append_row([kpi_name, today_str, actual, target, recorded_by, note])
        load_kpi_history.clear()
        return True
    except Exception as e:
        st.error(f"خطأ في حفظ السجل التاريخي: {e}")
        return False


def save_all_kpis_snapshot(df_kpi: pd.DataFrame, recorded_by: str) -> int:
    """
    يسجّل لقطة لجميع المؤشرات دفعةً واحدة (batch).
    يُحدِّث الصفوف الموجودة لنفس اليوم ويضيف الجديدة.
    يُرجع عدد السجلات المعالجة.
    """
    today_str = date.today().isoformat()
    try:
        sh = get_sheet_connection()
        ws = _get_or_create_history_ws(sh)
        existing  = ws.get_all_records()
        exist_map = {
            (str(r["KPI_Name"]).strip(), str(r["Date"]).strip()): i + 2
            for i, r in enumerate(existing)
        }
        new_rows   = []
        update_ops = []

        for _, row in df_kpi.iterrows():
            kpi    = str(row.get("KPI_Name", "")).strip()
            actual = safe_float(row.get("Actual", 0))
            target = safe_float(row.get("Target", 0))
            key    = (kpi, today_str)

            if key in exist_map:
                update_ops.append((exist_map[key],
                                   [kpi, today_str, actual, target, recorded_by, "لقطة شاملة"]))
            else:
                new_rows.append([kpi, today_str, actual, target, recorded_by, "لقطة شاملة"])

        for row_idx, data in update_ops:
            ws.update(f"A{row_idx}:F{row_idx}", [data])

        if new_rows:
            ws.append_rows(new_rows, value_input_option="USER_ENTERED")

        load_kpi_history.clear()
        return len(new_rows) + len(update_ops)
    except Exception as e:
        st.error(f"خطأ في اللقطة الشاملة: {e}")
        return 0


# ---------------------------------------------------------
# 6. دوال الرسم والتحليل التاريخي
# ---------------------------------------------------------

def compute_trend(series: pd.Series) -> dict:
    """يحلّل آخر قيمتين ويُرجع الاتجاه والنسبة والأيقونة."""
    vals = series.dropna().tolist()
    if len(vals) < 2:
        return {"direction": "flat", "pct": 0.0,
                "label": "لا يوجد سجل كافٍ", "css": "trend-flat", "icon": "➖"}
    last, prev = vals[-1], vals[-2]
    pct = ((last - prev) / abs(prev) * 100) if prev != 0 else (100.0 if last > 0 else 0.0)
    if   pct >  2: return {"direction":"up",   "pct":pct,  "label":f"▲ {pct:.1f}%",       "css":"trend-up",   "icon":"▲"}
    elif pct < -2: return {"direction":"down",  "pct":pct,  "label":f"▼ {abs(pct):.1f}%",  "css":"trend-down", "icon":"▼"}
    else:          return {"direction":"flat",  "pct":pct,  "label":"مستقر ➖",              "css":"trend-flat", "icon":"➖"}


def plot_kpi_trend(df_history: pd.DataFrame, kpi_name: str,
                   direction: str = "تصاعدي", unit: str = "", ctx: str = ""):
    """
    يرسم رسماً خطياً للاتجاه لمؤشر واحد.
    - خط الفعلي ملوَّن بناءً على الاتجاه
    - خط المستهدف منقّط
    - آخر قيمة مميّزة بنقطة أكبر
    - جدول البيانات قابل للطي
    """
    df = df_history[
        df_history["KPI_Name"].astype(str).str.strip() == kpi_name.strip()
    ].copy().sort_values("Date")

    if df.empty:
        st.info("لا توجد بيانات تاريخية بعد — سجّل أول قيمة باستخدام زر التحديث أو اللقطة الشاملة.")
        return

    trend = compute_trend(df["Actual"])

    # لون الخط حسب الاتجاه والمنطق (تصاعدي/تنازلي)
    if direction == "تنازلي":
        line_color = "#27ae60" if trend["direction"] == "down" else \
                     "#e74c3c" if trend["direction"] == "up"   else "#3498db"
    else:
        line_color = "#27ae60" if trend["direction"] == "up"   else \
                     "#e74c3c" if trend["direction"] == "down" else "#3498db"

    fig = go.Figure()

    # منطقة المستهدف
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Target"],
        mode="lines", name="المستهدف",
        line=dict(color="#e67e22", width=2, dash="dot"),
        hovertemplate="المستهدف: %{y}<extra></extra>"))

    # خط الفعلي
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Actual"],
        mode="lines+markers+text",
        name="الفعلي",
        line=dict(color=line_color, width=3),
        marker=dict(size=8, color=line_color, line=dict(color="white", width=2)),
        text=[f"{v:.1f}" for v in df["Actual"]],
        textposition="top center",
        textfont=dict(size=11, color=line_color),
        hovertemplate="<b>%{x|%Y-%m-%d}</b><br>الفعلي: %{y}<extra></extra>"))

    # نقطة آخر قيمة (مميّزة)
    last = df.iloc[-1]
    fig.add_trace(go.Scatter(
        x=[last["Date"]], y=[last["Actual"]],
        mode="markers", showlegend=False,
        marker=dict(size=15, color=line_color,
                    line=dict(color="white", width=3), symbol="circle"),
        hovertemplate=f"آخر قيمة: {last['Actual']:.1f}<extra></extra>"))

    fig.update_layout(
        title=dict(
            text=f"<b>{kpi_name[:45]}</b>   <span style='color:{line_color}'>{trend['label']}</span>",
            x=0.5, xanchor="center", font=dict(size=13)),
        xaxis=dict(title="", showgrid=True, gridcolor="#f0f0f0", tickformat="%b %Y"),
        yaxis=dict(title=unit or "القيمة", showgrid=True, gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=70, b=30, l=40, r=20), height=300,
        hovermode="x unified")

    safe_key = (kpi_name + ctx).replace(' ','_').replace('/','_').replace('-','_')[:80]
    st.plotly_chart(fig, use_container_width=True, key=f"trend_{safe_key}")

    with st.expander("📋 جدول البيانات التاريخية"):
        show = df[["Date", "Actual", "Target", "Recorded_By", "Note"]].copy()
        show["Date"] = show["Date"].dt.strftime("%Y-%m-%d")
        show.columns = ["التاريخ", "الفعلي", "المستهدف", "سجّل بواسطة", "ملاحظة"]
        st.dataframe(show.sort_values("التاريخ", ascending=False),
                     hide_index=True, use_container_width=True)


def show_history_overview(df_history: pd.DataFrame, df_kpi: pd.DataFrame):
    """نظرة عامة: رسم خطي لكل مجموعة في شبكة 2 عمود."""
    if df_history.empty:
        st.markdown(
            "<div class='snapshot-info'>📌 لا يوجد سجل تاريخي بعد — "
            "اضغط <b>تسجيل لقطة شاملة</b> لبدء التتبع.</div>",
            unsafe_allow_html=True)
        return

    cats = ["الكل"] + list(KPI_GROUPS.keys())
    sel  = st.selectbox("🔍 عرض مجموعة:", cats, key="ov_cat")

    recorded = df_history["KPI_Name"].astype(str).str.strip().unique().tolist()
    if sel == "الكل":
        kpis = recorded
    else:
        kpis = [k for k in KPI_GROUPS.get(sel, []) if k in recorded]

    if not kpis:
        st.info("لا توجد بيانات تاريخية للمجموعة المختارة بعد.")
        return

    cols = st.columns(2)
    for i, kpi in enumerate(kpis):
        kpi_info  = df_kpi[df_kpi["KPI_Name"].astype(str).str.strip() == kpi.strip()]
        unit      = kpi_info["Unit"].values[0]      if not kpi_info.empty and "Unit"      in kpi_info.columns else ""
        direction = kpi_info["Direction"].values[0] if not kpi_info.empty and "Direction" in kpi_info.columns else "تصاعدي"

        kpi_hist = df_history[df_history["KPI_Name"].astype(str).str.strip() == kpi.strip()].sort_values("Date")
        trend    = compute_trend(kpi_hist["Actual"])

        with cols[i % 2]:
            st.markdown(
                f"<div class='trend-card'>"
                f"<b>{kpi[:55]}</b><br>"
                f"<span class='{trend['css']}'>{trend['label']}</span>"
                f" &nbsp;|&nbsp; آخر قيمة: <b>{kpi_hist['Actual'].iloc[-1]:.1f}</b>"
                f"</div>",
                unsafe_allow_html=True)
            plot_kpi_trend(df_history, kpi, direction, unit, ctx="_ov")



# ---------------------------------------------------------
# 5. نظام المحادثة
# ---------------------------------------------------------
_CHAT_ICON = "📅"
_MSG_PATTERN = re.compile(
    r"📅\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})(?:\s*\[(\w+)\])?:\s*(.*?)(?=📅|\Z)",
    re.DOTALL,
)

def _parse_messages(text: str, default_role: str) -> list:
    if not text or str(text).strip() == "": return []
    msgs = []
    for m in _MSG_PATTERN.finditer(str(text)):
        dt_str = m.group(1).strip()
        role   = (m.group(2) or default_role).strip()
        body   = m.group(3).strip().replace("----------------", "").strip()
        if not body: continue
        try: dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        except: dt = datetime.min
        msgs.append({"dt": dt, "role": role, "text": body})
    return msgs

def _merge_and_sort(owner_text: str, admin_text: str) -> list:
    return sorted(
        _parse_messages(owner_text, "Owner") + _parse_messages(        "OIML project groups", "OIML-CS - number of services offered",
    ],
    "البحث والتطوير": [
        "عدد الابحاث العلمية المنشورة في مجلات مصنفة دولياً Q1, Q2",
        "عدد المشاركات العلمية الدولية", "عدد الطلاب الملتحقين",
        "عدد فعاليات الاستقطاب الجامعي", "عدد المشاريع الوطنية",
        "عدد المشاركين سنوياً في برامج التبادل الفني",
    ],
    "الكفاءة التشغيلية": [
        "نسبة نضج الحوكمة المؤسسية KAQA", "مؤشر التميز المؤسسي",
        "نسبة الإجراءات المؤتمتة", "مستوى رضا المستفيدين", "التحول الرقمي DGA",
        "نسبة الدوران الوظيفي", "نسبة الإيرادات الى إجمالي ميزانية",
        "نسبة النمو في إيرادات",
    ],
}

def get_kpi_category(kpi_name):
    kpi_name = str(kpi_name).strip()
    for group, items in KPI_GROUPS.items():
        if kpi_name in [str(i).strip() for i in items]:
            return group
    return "مؤشرات أخرى"

# ---------------------------------------------------------
# 3. اتصال Google Sheets
# ---------------------------------------------------------
SHEET_ID         = "11tKfYa-Sqa96wDwQvMvChgRWaxgMRAWAIvul7p27ayY"
KPI_HISTORY_SHEET = "KPI_History"   # الورقة الجديدة للتاريخ

def get_creds():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    try:
        if st.secrets is not None and 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if 'private_key' in creds_dict:
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
            return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception:
        pass
    if os.path.exists("credentials.json"):
        return ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    st.error("⚠️ خطأ في الاتصال: لم يتم العثور على ملف الاعتمادات أو Secrets.")
    st.stop()

def get_sheet_connection():
    creds  = get_creds()
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

# ---------------------------------------------------------
# 4. دوال مساعدة
# ---------------------------------------------------------
def safe_int(val):
    try:
        if str(val).strip() == '': return 0
        return int(float(str(val).replace('%', '').strip()))
    except: return 0

def safe_float(val):
    try:
        if str(val).strip() == '': return 0.0
        return float(str(val).replace('%', '').strip())
    except: return 0.0

def clean_df_for_gspread(df):
    df_clean = df.fillna("")
    return df_clean.astype(object).where(pd.notnull(df_clean), "")

def parse_date(date_str):
    try: return pd.to_datetime(date_str).date()
    except: return datetime.today().date()

def append_timestamped_comment(original_text, new_comment):
    if not new_comment or str(new_comment).strip() == "":
        return original_text
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = f"📅 {timestamp}: {str(new_comment).strip()}"
    if original_text and str(original_text).strip() != "":
        return f"{str(original_text)}\n----------------\n{new_entry}"
    return new_entry

def _last_update_date(comment_text: str):
    if not comment_text or str(comment_text).strip() == "": return None
    dates = re.findall(r"(\d{4}-\d{2}-\d{2})", str(comment_text))
    if not dates: return None
    try: return datetime.strptime(dates[-1], "%Y-%m-%d").date()
    except: return None

def _parse_end_date(val):
    try: return pd.to_datetime(str(val)).date()
    except: return None

# ---------------------------------------------------------
# 5. ═══════ نظام التتبع التاريخي ═══════
#
#  هيكل ورقة KPI_History (تُنشأ تلقائياً):
#  KPI_Name | Date | Actual | Target | Recorded_By | Note
# ---------------------------------------------------------

@st.cache_data(ttl=120, show_spinner=False)
def load_kpi_history(_cache_key: str) -> pd.DataFrame:
    """
    يحمّل جميع السجلات من ورقة KPI_History.
    يُنشئ الورقة تلقائياً إن لم تكن موجودة.
    مُخزَّن في cache لمدة دقيقتين.
    """
    COLS = ["KPI_Name", "Date", "Actual", "Target", "Recorded_By", "Note"]
    empty = pd.DataFrame(columns=COLS)
    try:
        sh = get_sheet_connection()
        try:
            ws = sh.worksheet(KPI_HISTORY_SHEET)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=KPI_HISTORY_SHEET, rows=2000, cols=6)
            ws.append_row(COLS)
            return empty

        records = ws.get_all_records()
        if not records:
            return empty

        df = pd.DataFrame(records)
        df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
        df["Actual"] = df["Actual"].apply(safe_float)
        df["Target"] = df["Target"].apply(safe_float)
        return df.dropna(subset=["Date"])
    except Exception as e:
        st.warning(f"تحذير: تعذّر تحميل السجل التاريخي — {e}")
        return empty


def _get_or_create_history_ws(sh):
    """يُرجع ورقة KPI_History، وينشئها إن لم تكن موجودة."""
    try:
        return sh.worksheet(KPI_HISTORY_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=KPI_HISTORY_SHEET, rows=2000, cols=6)
        ws.append_row(["KPI_Name", "Date", "Actual", "Target", "Recorded_By", "Note"])
        return ws


def save_kpi_snapshot(kpi_name: str, actual: float, target: float,
                      recorded_by: str, note: str = "") -> bool:
    """
    يحفظ لقطة مؤشر واحد في KPI_History.
    إذا كان اليوم مُسجَّلاً بالفعل → يُحدِّث الصف بدلاً من تكراره.
    يُستدعى تلقائياً من زر "حفظ تحديث المؤشر" في owner_view.
    """
    today_str = date.today().isoformat()
    try:
        sh = get_sheet_connection()
        ws = _get_or_create_history_ws(sh)
        records = ws.get_all_records()

        for i, r in enumerate(records):
            if (str(r.get("KPI_Name","")).strip() == kpi_name.strip()
                    and str(r.get("Date","")).strip() == today_str):
                row_idx = i + 2   # +1 للـ header, +1 لـ 1-based
                ws.update(f"A{row_idx}:F{row_idx}",
                          [[kpi_name, today_str, actual, target, recorded_by, note]])
                load_kpi_history.clear()
                return True

        ws.append_row([kpi_name, today_str, actual, target, recorded_by, note])
        load_kpi_history.clear()
        return True
    except Exception as e:
        st.error(f"خطأ في حفظ السجل التاريخي: {e}")
        return False


def save_all_kpis_snapshot(df_kpi: pd.DataFrame, recorded_by: str) -> int:
    """
    يسجّل لقطة لجميع المؤشرات دفعةً واحدة (batch).
    يُحدِّث الصفوف الموجودة لنفس اليوم ويضيف الجديدة.
    يُرجع عدد السجلات المعالجة.
    """
    today_str = date.today().isoformat()
    try:
        sh = get_sheet_connection()
        ws = _get_or_create_history_ws(sh)
        existing  = ws.get_all_records()
        exist_map = {
            (str(r["KPI_Name"]).strip(), str(r["Date"]).strip()): i + 2
            for i, r in enumerate(existing)
        }
        new_rows   = []
        update_ops = []

        for _, row in df_kpi.iterrows():
            kpi    = str(row.get("KPI_Name", "")).strip()
            actual = safe_float(row.get("Actual", 0))
            target = safe_float(row.get("Target", 0))
            key    = (kpi, today_str)

            if key in exist_map:
                update_ops.append((exist_map[key],
                                   [kpi, today_str, actual, target, recorded_by, "لقطة شاملة"]))
            else:
                new_rows.append([kpi, today_str, actual, target, recorded_by, "لقطة شاملة"])

        for row_idx, data in update_ops:
            ws.update(f"A{row_idx}:F{row_idx}", [data])

        if new_rows:
            ws.append_rows(new_rows, value_input_option="USER_ENTERED")

        load_kpi_history.clear()
        return len(new_rows) + len(update_ops)
    except Exception as e:
        st.error(f"خطأ في اللقطة الشاملة: {e}")
        return 0


# ---------------------------------------------------------
# 6. دوال الرسم والتحليل التاريخي
# ---------------------------------------------------------

def compute_trend(series: pd.Series) -> dict:
    """يحلّل آخر قيمتين ويُرجع الاتجاه والنسبة والأيقونة."""
    vals = series.dropna().tolist()
    if len(vals) < 2:
        return {"direction": "flat", "pct": 0.0,
                "label": "لا يوجد سجل كافٍ", "css": "trend-flat", "icon": "➖"}
    last, prev = vals[-1], vals[-2]
    pct = ((last - prev) / abs(prev) * 100) if prev != 0 else (100.0 if last > 0 else 0.0)
    if   pct >  2: return {"direction":"up",   "pct":pct,  "label":f"▲ {pct:.1f}%",       "css":"trend-up",   "icon":"▲"}
    elif pct < -2: return {"direction":"down",  "pct":pct,  "label":f"▼ {abs(pct):.1f}%",  "css":"trend-down", "icon":"▼"}
    else:          return {"direction":"flat",  "pct":pct,  "label":"مستقر ➖",              "css":"trend-flat", "icon":"➖"}


def plot_kpi_trend(df_history: pd.DataFrame, kpi_name: str,
                   direction: str = "تصاعدي", unit: str = "", ctx: str = ""):
    """
    يرسم رسماً خطياً للاتجاه لمؤشر واحد.
    - خط الفعلي ملوَّن بناءً على الاتجاه
    - خط المستهدف منقّط
    - آخر قيمة مميّزة بنقطة أكبر
    - جدول البيانات قابل للطي
    """
    df = df_history[
        df_history["KPI_Name"].astype(str).str.strip() == kpi_name.strip()
    ].copy().sort_values("Date")

    if df.empty:
        st.info("لا توجد بيانات تاريخية بعد — سجّل أول قيمة باستخدام زر التحديث أو اللقطة الشاملة.")
        return

    trend = compute_trend(df["Actual"])

    # لون الخط حسب الاتجاه والمنطق (تصاعدي/تنازلي)
    if direction == "تنازلي":
        line_color = "#27ae60" if trend["direction"] == "down" else \
                     "#e74c3c" if trend["direction"] == "up"   else "#3498db"
    else:
        line_color = "#27ae60" if trend["direction"] == "up"   else \
                     "#e74c3c" if trend["direction"] == "down" else "#3498db"

    fig = go.Figure()

    # منطقة المستهدف
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Target"],
        mode="lines", name="المستهدف",
        line=dict(color="#e67e22", width=2, dash="dot"),
        hovertemplate="المستهدف: %{y}<extra></extra>"))

    # خط الفعلي
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Actual"],
        mode="lines+markers+text",
        name="الفعلي",
        line=dict(color=line_color, width=3),
        marker=dict(size=8, color=line_color, line=dict(color="white", width=2)),
        text=[f"{v:.1f}" for v in df["Actual"]],
        textposition="top center",
        textfont=dict(size=11, color=line_color),
        hovertemplate="<b>%{x|%Y-%m-%d}</b><br>الفعلي: %{y}<extra></extra>"))

    # نقطة آخر قيمة (مميّزة)
    last = df.iloc[-1]
    fig.add_trace(go.Scatter(
        x=[last["Date"]], y=[last["Actual"]],
        mode="markers", showlegend=False,
        marker=dict(size=15, color=line_color,
                    line=dict(color="white", width=3), symbol="circle"),
        hovertemplate=f"آخر قيمة: {last['Actual']:.1f}<extra></extra>"))

    fig.update_layout(
        title=dict(
            text=f"<b>{kpi_name[:45]}</b>   <span style='color:{line_color}'>{trend['label']}</span>",
            x=0.5, xanchor="center", font=dict(size=13)),
        xaxis=dict(title="", showgrid=True, gridcolor="#f0f0f0", tickformat="%b %Y"),
        yaxis=dict(title=unit or "القيمة", showgrid=True, gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=70, b=30, l=40, r=20), height=300,
        hovermode="x unified")

    safe_key = (kpi_name + ctx).replace(' ','_').replace('/','_').replace('-','_')[:80]
    st.plotly_chart(fig, use_container_width=True, key=f"trend_{safe_key}")

    with st.expander("📋 جدول البيانات التاريخية"):
        show = df[["Date", "Actual", "Target", "Recorded_By", "Note"]].copy()
        show["Date"] = show["Date"].dt.strftime("%Y-%m-%d")
        show.columns = ["التاريخ", "الفعلي", "المستهدف", "سجّل بواسطة", "ملاحظة"]
        st.dataframe(show.sort_values("التاريخ", ascending=False),
                     hide_index=True, use_container_width=True)


def show_history_overview(df_history: pd.DataFrame, df_kpi: pd.DataFrame):
    """نظرة عامة: رسم خطي لكل مجموعة في شبكة 2 عمود."""
    if df_history.empty:
        st.markdown(
            "<div class='snapshot-info'>📌 لا يوجد سجل تاريخي بعد — "
            "اضغط <b>تسجيل لقطة شاملة</b> لبدء التتبع.</div>",
            unsafe_allow_html=True)
        return

    cats = ["الكل"] + list(KPI_GROUPS.keys())
    sel  = st.selectbox("🔍 عرض مجموعة:", cats, key="ov_cat")

    recorded = df_history["KPI_Name"].astype(str).str.strip().unique().tolist()
    if sel == "الكل":
        kpis = recorded
    else:
        kpis = [k for k in KPI_GROUPS.get(sel, []) if k in recorded]

    if not kpis:
        st.info("لا توجد بيانات تاريخية للمجموعة المختارة بعد.")
        return

    cols = st.columns(2)
    for i, kpi in enumerate(kpis):
        kpi_info  = df_kpi[df_kpi["KPI_Name"].astype(str).str.strip() == kpi.strip()]
        unit      = kpi_info["Unit"].values[0]      if not kpi_info.empty and "Unit"      in kpi_info.columns else ""
        direction = kpi_info["Direction"].values[0] if not kpi_info.empty and "Direction" in kpi_info.columns else "تصاعدي"

        kpi_hist = df_history[df_history["KPI_Name"].astype(str).str.strip() == kpi.strip()].sort_values("Date")
        trend    = compute_trend(kpi_hist["Actual"])

        with cols[i % 2]:
            st.markdown(
                f"<div class='trend-card'>"
                f"<b>{kpi[:55]}</b><br>"
                f"<span class='{trend['css']}'>{trend['label']}</span>"
                f" &nbsp;|&nbsp; آخر قيمة: <b>{kpi_hist['Actual'].iloc[-1]:.1f}</b>"
                f"</div>",
                unsafe_allow_html=True)
            plot_kpi_trend(df_history, kpi, direction, unit, ctx="_ov")



# ---------------------------------------------------------
# 5. نظام المحادثة
# ---------------------------------------------------------
_MSG_PATTERN = re.compile(
    r"\U0001f4c5\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})(?:\s*\[(\w+)\])?:\s*(.*?)(?=\U0001f4c5|\Z)",
    re.DOTALL,
)

def _parse_messages(text: str, default_role: str) -> list:
    if not text or str(text).strip() == "": return []
    msgs = []
    for m in _MSG_PATTERN.finditer(str(text)):
        dt_str = m.group(1).strip()
        role   = (m.group(2) or default_role).strip()
        body   = m.group(3).strip().replace("----------------", "").strip()
        if not body: continue
        try: dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        except: dt = datetime.min
        msgs.append({"dt": dt, "role": role, "text": body})
    return msgs

def _merge_and_sort(owner_text: str, admin_text: str) -> list:
    return sorted(
        _parse_messages(owner_text, "Owner") + _parse_messages(ad
