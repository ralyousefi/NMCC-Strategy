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
# 1. إعدادات الصفحة والتصميم
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
        border: 1px solid #ffeeba; border-right: 5px solid #ffc107; margin-bottom: 20px; font-weight: bold;
    }
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background: #f1f1f1; color: #555; text-align: center;
        padding: 10px; font-size: 12px; border-top: 1px solid #ddd; z-index: 100;
    }

    /* تنبيهات */
    .alert-summary-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin-bottom: 20px; }
    .alert-summary-card { border-radius: 10px; padding: 16px; text-align: center; }
    .alert-summary-card .num { font-size: 32px; font-weight: 900; line-height: 1; }
    .alert-summary-card .lbl { font-size: 13px; margin-top: 4px; opacity: .85; }
    .s-red    { background: #fde8e8; color: #c0392b; }
    .s-orange { background: #fef3cd; color: #d35400; }
    .s-blue   { background: #e8f4fd; color: #1a5276; }
    .s-gray   { background: #f3f3f3; color: #2c3e50; }
    .alert-header { display: flex; align-items: center; gap: 10px; padding: 14px 18px; border-radius: 10px; margin-bottom: 8px; font-weight: bold; direction: rtl; }
    .alert-overdue { background: #fde8e8; border-right: 5px solid #c0392b; color: #7b241c; }
    .alert-at-risk { background: #fef3cd; border-right: 5px solid #e67e22; color: #784212; }
    .all-good { background: #eafaf1; border-right: 5px solid #27ae60; border-radius: 8px; padding: 12px 18px; color: #1e8449; font-weight: bold; margin-bottom: 10px; direction: rtl; }

    /* محادثة وتتبع */
    .trend-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 14px 18px; margin-bottom: 12px; }
    .trend-up   { color: #27ae60; font-weight: bold; font-size: 15px; }
    .trend-down { color: #e74c3c; font-weight: bold; font-size: 15px; }
    .trend-flat { color: #f39c12; font-weight: bold; font-size: 15px; }
    .snapshot-info { background: #f0f4ff; border-radius: 8px; padding: 10px 16px; border-right: 4px solid #3498db; margin-bottom: 12px; font-size: 14px; }
    
    .chat-wrap { display: flex; flex-direction: column; gap: 10px; padding: 12px 4px; direction: rtl; }
    .bubble { max-width: 78%; padding: 10px 14px; border-radius: 16px; font-size: 13.5px; line-height: 1.6; word-break: break-word; font-family: 'Tajawal', sans-serif; }
    .bubble-admin { background: #1a237e; color: #fff; align-self: flex-end; border-bottom-right-radius: 4px; margin-left: auto; }
    .bubble-admin .meta { font-size: 11px; opacity: .7; margin-bottom: 4px; }
    .bubble-owner { background: #f0f4ff; color: #1a237e; border: 1px solid #dce4ff; align-self: flex-start; border-bottom-left-radius: 4px; margin-right: auto; }
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
# 3. اتصال Google Sheets وجلب البيانات (مع Caching)
# ---------------------------------------------------------
SHEET_ID         = "11tKfYa-Sqa96wDwQvMvChgRWaxgMRAWAIvul7p27ayY"
KPI_HISTORY_SHEET = "KPI_History"

def get_creds():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
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

@st.cache_data(ttl=300, show_spinner=False)
def load_activities_data():
    try:
        sh = get_sheet_connection()
        ws_acts = sh.worksheet("Activities")
        df = pd.DataFrame(ws_acts.get_all_records())
        df['Progress'] = df['Progress'].apply(safe_int)
        for c in ['Admin_Comment', 'Owner_Comment']:
            if c not in df.columns: df[c] = ""
        return df
    except Exception as e:
        st.error(f"خطأ في تحميل الأنشطة: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def load_kpis_data():
    try:
        sh = get_sheet_connection()
        ws_kpi = sh.worksheet("KPIs")
        df = pd.DataFrame(ws_kpi.get_all_records())
        for c in ['Admin_Comment','Owner_Comment','Owner']:
            if c not in df.columns: df[c] = ""
        df['Target'] = df['Target'].apply(safe_float)
        df['Actual'] = df['Actual'].apply(safe_float)
        return df
    except Exception as e:
        st.error(f"خطأ في تحميل المؤشرات: {e}")
        return pd.DataFrame()

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
    if not new_comment or str(new_comment).strip() == "": return original_text
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
# 5. نظام التتبع التاريخي
# ---------------------------------------------------------
@st.cache_data(ttl=120, show_spinner=False)
def load_kpi_history(_cache_key: str = SHEET_ID) -> pd.DataFrame:
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
        if not records: return empty
        df = pd.DataFrame(records)
        df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
        df["Actual"] = df["Actual"].apply(safe_float)
        df["Target"] = df["Target"].apply(safe_float)
        return df.dropna(subset=["Date"])
    except Exception as e:
        st.warning(f"تحذير: تعذّر تحميل السجل التاريخي — {e}")
        return empty

def _get_or_create_history_ws(sh):
    try: return sh.worksheet(KPI_HISTORY_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=KPI_HISTORY_SHEET, rows=2000, cols=6)
        ws.append_row(["KPI_Name", "Date", "Actual", "Target", "Recorded_By", "Note"])
        return ws

def save_kpi_snapshot(kpi_name: str, actual: float, target: float, recorded_by: str, note: str = "") -> bool:
    today_str = date.today().isoformat()
    try:
        sh = get_sheet_connection()
        ws = _get_or_create_history_ws(sh)
        records = ws.get_all_records()
        for i, r in enumerate(records):
            if str(r.get("KPI_Name","")).strip() == kpi_name.strip() and str(r.get("Date","")).strip() == today_str:
                row_idx = i + 2
                ws.update(f"A{row_idx}:F{row_idx}", [[kpi_name, today_str, actual, target, recorded_by, note]])
                load_kpi_history.clear()
                return True
        ws.append_row([kpi_name, today_str, actual, target, recorded_by, note])
        load_kpi_history.clear()
        return True
    except Exception as e:
        st.error(f"خطأ في حفظ السجل التاريخي: {e}")
        return False

def save_all_kpis_snapshot(df_kpi: pd.DataFrame, recorded_by: str) -> int:
    today_str = date.today().isoformat()
    try:
        sh = get_sheet_connection()
        ws = _get_or_create_history_ws(sh)
        existing  = ws.get_all_records()
        exist_map = { (str(r["KPI_Name"]).strip(), str(r["Date"]).strip()): i + 2 for i, r in enumerate(existing) }
        new_rows, update_ops = [], []

        for _, row in df_kpi.iterrows():
            kpi    = str(row.get("KPI_Name", "")).strip()
            actual = safe_float(row.get("Actual", 0))
            target = safe_float(row.get("Target", 0))
            key    = (kpi, today_str)

            if key in exist_map:
                update_ops.append((exist_map[key], [kpi, today_str, actual, target, recorded_by, "لقطة شاملة"]))
            else:
                new_rows.append([kpi, today_str, actual, target, recorded_by, "لقطة شاملة"])

        for row_idx, data in update_ops: ws.update(f"A{row_idx}:F{row_idx}", [data])
        if new_rows: ws.append_rows(new_rows, value_input_option="USER_ENTERED")
        
        load_kpi_history.clear()
        return len(new_rows) + len(update_ops)
    except Exception as e:
        st.error(f"خطأ في اللقطة الشاملة: {e}"); return 0

# ---------------------------------------------------------
# 6. دوال الرسم والتحليل التاريخي
# ---------------------------------------------------------
def compute_trend(series: pd.Series) -> dict:
    vals = series.dropna().tolist()
    if len(vals) < 2: return {"direction": "flat", "pct": 0.0, "label": "لا يوجد سجل كافٍ", "css": "trend-flat", "icon": "➖"}
    last, prev = vals[-1], vals[-2]
    pct = ((last - prev) / abs(prev) * 100) if prev != 0 else (100.0 if last > 0 else 0.0)
    if   pct >  2: return {"direction":"up",   "pct":pct,  "label":f"▲ {pct:.1f}%",       "css":"trend-up",   "icon":"▲"}
    elif pct < -2: return {"direction":"down",  "pct":pct,  "label":f"▼ {abs(pct):.1f}%",  "css":"trend-down", "icon":"▼"}
    else:          return {"direction":"flat",  "pct":pct,  "label":"مستقر ➖",              "css":"trend-flat", "icon":"➖"}

def plot_kpi_trend(df_history: pd.DataFrame, kpi_name: str, direction: str = "تصاعدي", unit: str = "", ctx: str = ""):
    df = df_history[df_history["KPI_Name"].astype(str).str.strip() == kpi_name.strip()].copy().sort_values("Date")
    if df.empty:
        st.info("لا توجد بيانات تاريخية بعد."); return
    trend = compute_trend(df["Actual"])
    
    if direction == "تنازلي": line_color = "#27ae60" if trend["direction"] == "down" else "#e74c3c" if trend["direction"] == "up" else "#3498db"
    else: line_color = "#27ae60" if trend["direction"] == "up" else "#e74c3c" if trend["direction"] == "down" else "#3498db"

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Target"], mode="lines", name="المستهدف", line=dict(color="#e67e22", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Actual"], mode="lines+markers+text", name="الفعلي",
        line=dict(color=line_color, width=3), marker=dict(size=8, color=line_color, line=dict(color="white", width=2)),
        text=[f"{v:.1f}" for v in df["Actual"]], textposition="top center", textfont=dict(size=11, color=line_color)))
    
    last = df.iloc[-1]
    fig.add_trace(go.Scatter(x=[last["Date"]], y=[last["Actual"]], mode="markers", showlegend=False,
        marker=dict(size=15, color=line_color, line=dict(color="white", width=3), symbol="circle")))

    fig.update_layout(
        title=dict(text=f"<b>{kpi_name[:45]}</b> <span style='color:{line_color}'>{trend['label']}</span>", x=0.5, font=dict(size=13)),
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0", tickformat="%b %Y"), yaxis=dict(title=unit or "القيمة", showgrid=True, gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"), plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=70, b=30, l=40, r=20), height=300, hovermode="x unified")

    st.plotly_chart(fig, use_container_width=True, key=f"trend_{kpi_name[:20]}_{ctx}")
    with st.expander("📋 جدول البيانات التاريخية"):
        show = df[["Date", "Actual", "Target", "Recorded_By", "Note"]].copy()
        show["Date"] = show["Date"].dt.strftime("%Y-%m-%d")
        show.columns = ["التاريخ", "الفعلي", "المستهدف", "سجّل بواسطة", "ملاحظة"]
        st.dataframe(show.sort_values("التاريخ", ascending=False), hide_index=True, use_container_width=True)

def show_history_overview(df_history: pd.DataFrame, df_kpi: pd.DataFrame):
    if df_history.empty:
        st.markdown("<div class='snapshot-info'>📌 لا يوجد سجل تاريخي بعد.</div>", unsafe_allow_html=True); return
    cats = ["الكل"] + list(KPI_GROUPS.keys())
    sel  = st.selectbox("🔍 عرض مجموعة:", cats, key="ov_cat")
    recorded = df_history["KPI_Name"].astype(str).str.strip().unique().tolist()
    kpis = recorded if sel == "الكل" else [k for k in KPI_GROUPS.get(sel, []) if k in recorded]
    if not kpis: st.info("لا توجد بيانات."); return

    cols = st.columns(2)
    for i, kpi in enumerate(kpis):
        kpi_info = df_kpi[df_kpi["KPI_Name"].astype(str).str.strip() == kpi.strip()]
        unit = kpi_info["Unit"].values[0] if not kpi_info.empty and "Unit" in kpi_info.columns else ""
        direction = kpi_info["Direction"].values[0] if not kpi_info.empty and "Direction" in kpi_info.columns else "تصاعدي"
        with cols[i % 2]: plot_kpi_trend(df_history, kpi, direction, unit, ctx=f"_ov_{i}")

# ---------------------------------------------------------
# 7. نظام المحادثة
# ---------------------------------------------------------
_MSG_PATTERN = re.compile(r"📅\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})(?:\s*\[(\w+)\])?:\s*(.*?)(?=📅|\Z)", re.DOTALL)

def _parse_messages(text: str, default_role: str) -> list:
    if not text or str(text).strip() == "": return []
    msgs = []
    for m in _MSG_PATTERN.finditer(str(text)):
        dt_str, role, body = m.group(1).strip(), (m.group(2) or default_role).strip(), m.group(3).strip().replace("----------------", "").strip()
        if not body: continue
        try: dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        except: dt = datetime.min
        msgs.append({"dt": dt, "role": role, "text": body})
    return msgs

def _render_chat(messages: list):
    if not messages:
        st.markdown("<div class='chat-empty'>💬 لا توجد رسائل بعد</div>", unsafe_allow_html=True); return
    html = "<div class='chat-wrap'>"
    prev_date = None
    for msg in messages:
        msg_date = msg["dt"].strftime("%Y-%m-%d")
        if msg_date != prev_date:
            html += f"<div class='chat-divider'>── {msg_date} ──</div>"
            prev_date = msg_date
        is_admin = (msg["role"] == "Admin")
        cls, sender, justify = ("bubble-admin", "المدير", "flex-end") if is_admin else ("bubble-owner", "الموظف", "flex-start")
        text_esc = msg["text"].replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
        html += f"<div style='display:flex;justify-content:{justify}'><div class='bubble {cls}'><div class='meta'>{sender} · {msg['dt'].strftime('%H:%M')}</div>{text_esc}</div></div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# ---------------------------------------------------------
# 8. التنبيهات والتحليل
# ---------------------------------------------------------
def analyze_activities(df: pd.DataFrame) -> dict:
    today  = date.today()
    result = {"overdue": [], "at_risk": [], "stale": [], "no_comment": []}
    for _, row in df.iterrows():
        mab, act, prog = str(row.get("Mabadara","")).strip(), str(row.get("Activity", "")).strip(), safe_int(row.get("Progress", 0))
        end = _parse_end_date(row.get("End_Date",""))
        oc = str(row.get("Owner_Comment","")).strip()
        base = {"مبادرة": (mab[:30]+"…") if len(mab)>30 else mab, "النشاط": (act[:45]+"…") if len(act)>45 else act, "الإنجاز": prog}
        
        if end and prog < 100 and end < today: result["overdue"].append({**base,"تاريخ الانتهاء":str(end),"أيام التأخير":(today - end).days})
        elif end and 0 <= (end - today).days <= 14 and prog < 80: result["at_risk"].append({**base,"تاريخ الانتهاء":str(end),"أيام متبقية":(end - today).days})
        
        lu = _last_update_date(oc)
        if lu and (today-lu).days > 21: result["stale"].append({**base,"آخر تحديث":str(lu),"أيام منذ التحديث":(today-lu).days})
        if not oc and prog < 100: result["no_comment"].append({**base})
    return result

def analyze_kpis_alerts(df_kpi: pd.DataFrame) -> list:
    alerts, today = [], date.today()
    for _, row in df_kpi.iterrows():
        kpi, own, tgt, act = str(row.get("KPI_Name","")).strip(), str(row.get("Owner","")).strip(), safe_float(row.get("Target",0)), safe_float(row.get("Actual",0))
        drx, cmt, reas = str(row.get("Direction","تصاعدي")).strip(), str(row.get("Owner_Comment","")).strip(), []
        
        if drx == "تصاعدي":
            if tgt>0 and act==0: reas.append("المتحقق = 0")
            elif tgt>0 and (act/tgt)<0.5: reas.append(f"المتحقق {round((act/tgt)*100)}% من المستهدف")
        elif act>tgt*1.5 and tgt>0: reas.append("تجاوز الحد الأعلى")
        
        lu = _last_update_date(cmt)
        if lu and (today-lu).days>30: reas.append(f"لم يُحدَّث منذ {(today-lu).days} يوماً")
        elif not cmt: reas.append("لا يوجد تعليق")
        
        if reas: alerts.append({"المؤشر": (kpi[:40]+"…") if len(kpi)>40 else kpi,"المسؤول":own,"المستهدف":tgt,"المتحقق":act,"السبب":" | ".join(reas)})
    return alerts

def show_alerts_panel(df_acts: pd.DataFrame, df_kpi: pd.DataFrame = None):
    alerts = analyze_activities(df_acts)
    total_acts = sum(len(v) for v in alerts.values())
    kpi_alerts = analyze_kpis_alerts(df_kpi) if df_kpi is not None else []
    st.markdown("## 🔔 مركز التنبيهات")
    if total_acts == 0 and not kpi_alerts:
        st.markdown("<div class='all-good'>✅ لا توجد تنبيهات — جميع الأنشطة والمؤشرات على المسار الصحيح</div>", unsafe_allow_html=True); st.markdown("---"); return
    
    st.markdown(f"""
    <div class="alert-summary-grid">
      <div class="alert-summary-card s-red"><div class="num">{len(alerts['overdue'])}</div><div class="lbl">🚨 متأخرة</div></div>
      <div class="alert-summary-card s-orange"><div class="num">{len(alerts['at_risk'])}</div><div class="lbl">⚠️ في خطر (14 يوم)</div></div>
      <div class="alert-summary-card s-blue"><div class="num">{len(alerts['stale'])}</div><div class="lbl">🕐 لم تُحدَّث (21 يوم)</div></div>
      <div class="alert-summary-card s-gray"><div class="num">{len(alerts['no_comment'])}</div><div class="lbl">📭 بدون تعليق</div></div>
    </div>""", unsafe_allow_html=True)
    
    with st.expander(f"🚨 الأنشطة المتأخرة ({len(alerts['overdue'])})", expanded=bool(alerts["overdue"])):
        if alerts["overdue"]: st.dataframe(pd.DataFrame(alerts["overdue"]), hide_index=True, use_container_width=True)
    with st.expander(f"⚠️ في خطر ({len(alerts['at_risk'])})"):
        if alerts["at_risk"]: st.dataframe(pd.DataFrame(alerts["at_risk"]), hide_index=True, use_container_width=True)
    st.markdown("---")

# ---------------------------------------------------------
# 9. تسجيل الدخول
# ---------------------------------------------------------
if 'logged_in' not in st.session_state: st.session_state.update({'logged_in': False, 'user_info': {}})

def login():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h2 style='text-align:center;'>🔐 تسجيل الدخول</h2><br>", unsafe_allow_html=True)
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("دخول", use_container_width=True):
            try:
                users_df = pd.DataFrame(get_sheet_connection().worksheet("Users").get_all_records())
                user = users_df[users_df['username'].astype(str).str.strip() == username.strip()]
                if not user.empty and str(user.iloc[0]['password']) == str(password):
                    st.session_state.update({'logged_in': True, 'user_info': user.iloc[0].to_dict()})
                    st.rerun()
                else: st.error("بيانات الدخول غير صحيحة")
            except Exception as e: st.error(f"خطأ اتصال: {e}")

# ---------------------------------------------------------
# 10. واجهة المدير (محسنة: Drill-Down للمبادرات)
# ---------------------------------------------------------
def admin_view(user_name):
    st.markdown("### 📊 لوحة القيادة التنفيذية")
    
    df_acts = load_activities_data()
    df_kpi  = load_kpis_data()
    
    if not df_acts.empty:
        today_dt = datetime.now().date()
        df_acts['_end'] = pd.to_datetime(df_acts['End_Date'], errors='coerce').dt.date
        df_acts['_is_overdue'] = (df_acts['Progress'] < 100) & (df_acts['_end'] < today_dt)
        k1,k2,k3,k4 = st.columns(4)
        k1.metric("📦 المبادرات", df_acts['Mabadara'].nunique())
        k2.metric("📝 الأنشطة", len(df_acts))
        k3.metric("📈 متوسط الإنجاز", f"{df_acts['Progress'].mean():.1f}%")
        k4.metric("🚨 أنشطة متأخرة", df_acts['_is_overdue'].sum(), delta_color="inverse")
        st.markdown("---")

    show_alerts_panel(df_acts, df_kpi)

    tab1, tab2, tab3 = st.tabs(["📋 ملخص وتفاصيل المبادرات", "📊 مؤشرات الأداء والتاريخ", "💬 المحادثات"])

    # --- التبويب 1: المبادرات (Drill-Down) ---
    with tab1:
        st.markdown("#### 🎯 ملخص حالة المبادرات (الصورة الكبرى)")
        if not df_acts.empty:
            init_summary = df_acts.groupby('Mabadara').agg(
                Total_Acts=('Activity', 'count'), Avg_Prog=('Progress', 'mean'), Overdue=('_is_overdue', 'sum')
            ).reset_index()
            
            st.dataframe(init_summary, column_config={
                "Mabadara": "اسم المبادرة", "Total_Acts": "إجمالي الأنشطة",
                "Avg_Prog": st.column_config.ProgressColumn("متوسط الإنجاز", format="%d%%", min_value=0, max_value=100),
                "Overdue": st.column_config.NumberColumn("متأخرة 🚨")
            }, hide_index=True, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 🔍 تفاصيل الأنشطة وإضافة التوجيهات")
            sel_init = st.selectbox("اختر مبادرة للتدخل وإضافة الملاحظات:", [""] + init_summary['Mabadara'].tolist())
            
            if sel_init:
                with st.expander(f"أنشطة مبادرة: {sel_init}", expanded=True):
                    df_filt = df_acts[df_acts['Mabadara'] == sel_init].copy()
                    df_filt['New_Admin_Note'] = ""
                    edited = st.data_editor(df_filt[['Activity', 'Progress', 'End_Date', 'Owner_Comment', 'New_Admin_Note', 'Mabadara']], 
                        column_config={
                            "Activity": st.column_config.TextColumn("النشاط", disabled=True),
                            "Progress": st.column_config.ProgressColumn("الإنجاز %", format="%d%%", min_value=0, max_value=100, disabled=True),
                            "End_Date": st.column_config.TextColumn("النهاية", disabled=True),
                            "Owner_Comment": st.column_config.TextColumn("رد الموظف", disabled=True),
                            "New_Admin_Note": st.column_config.TextColumn("✍️ توجيه جديد للموظف (اكتب هنا)"),
                            "Mabadara": None
                        }, hide_index=True, use_container_width=True, key=f"ed_{sel_init}")
                    
                    if st.button("💾 إرسال التوجيهات"):
                        changed = False
                        df_save = load_activities_data().copy() # تحميل النسخة الأحدث
                        for _, row in edited.iterrows():
                            nn = str(row['New_Admin_Note']).strip()
                            if nn:
                                mask = (df_save['Mabadara'] == sel_init) & (df_save['Activity'] == row['Activity'])
                                df_save.loc[mask, 'Admin_Comment'] = append_timestamped_comment(df_save.loc[mask, 'Admin_Comment'].values[0], nn)
                                changed = True
                        if changed:
                            sh = get_sheet_connection()
                            sh.worksheet("Activities").update(values=[clean_df_for_gspread(df_save).columns.tolist()] + clean_df_for_gspread(df_save).values.tolist(), range_name='A1')
                            load_activities_data.clear() # تفريغ الكاش
                            st.success("✅ تم حفظ التوجيهات وإرسالها للموظف!"); time.sleep(1); st.rerun()

    # --- التبويب 2: المؤشرات والتاريخ ---
    with tab2:
        if not df_kpi.empty:
            st.markdown("#### ✏️ تحديث المؤشرات")
            fc = st.selectbox("📂 فلترة:", ["الكل"] + list(KPI_GROUPS.keys()))
            df_kpi['Category'] = df_kpi['KPI_Name'].apply(get_kpi_category)
            dfe = df_kpi[df_kpi['Category']==fc].copy() if fc!="الكل" else df_kpi.copy()
            dfe['New_Admin_Note'] = ""
            ek = st.data_editor(dfe[['KPI_Name', 'Target', 'Actual', 'Owner', 'Owner_Comment', 'New_Admin_Note']], 
                column_config={"New_Admin_Note": st.column_config.TextColumn("✍️ ملاحظة جديدة")},
                disabled=["KPI_Name", "Actual", "Owner", "Owner_Comment"], hide_index=True, use_container_width=True)
            if st.button("💾 حفظ تحديثات المؤشرات"):
                df_save_kpi = load_kpis_data().copy()
                changed = False
                for _, row in ek.iterrows():
                    mask = df_save_kpi['KPI_Name'] == row['KPI_Name']
                    if float(row['Target']) != float(df_save_kpi.loc[mask,'Target'].values[0]):
                        df_save_kpi.loc[mask,'Target'] = row['Target']; changed=True
                    nn = str(row['New_Admin_Note']).strip()
                    if nn:
                        df_save_kpi.loc[mask,'Admin_Comment'] = append_timestamped_comment(df_save_kpi.loc[mask,'Admin_Comment'].values[0], nn); changed=True
                if changed:
                    get_sheet_connection().worksheet("KPIs").update(values=[clean_df_for_gspread(df_save_kpi).columns.tolist()] + clean_df_for_gspread(df_save_kpi).values.tolist(), range_name='A1')
                    load_kpis_data.clear(); st.success("✅ تم الحفظ!"); time.sleep(1); st.rerun()
            st.markdown("---")
            st.markdown("#### 📷 تسجيل لقطة شاملة للمؤشرات (نهاية الربع)")
            if st.button("تسجيل لقطة الآن", type="primary"):
                n = save_all_kpis_snapshot(df_kpi, user_name)
                if n > 0: st.success("تم الحفظ بنجاح")

    # --- التبويب 3: المحادثات ---
    with tab3:
        st.info("قم باختيار المبادرة والنشاط لعرض سجل المحادثات الزمني بينك وبين الموظف.")

# ---------------------------------------------------------
# 11. واجهة المالك (الموظف)
# ---------------------------------------------------------
def owner_view(user_name, my_initiatives_str):
    my_list = [x.strip() for x in str(my_initiatives_str).split(',') if x.strip()] if my_initiatives_str else []
    df_acts = load_activities_data()
    df_kpi  = load_kpis_data()
    my_data = df_acts[df_acts['Mabadara'].isin(my_list)].copy()
    
    st.markdown("### 📌 لوحة إنجاز الأنشطة")
    if not my_list: st.warning("⚠️ لا توجد مبادرات مسندة إليك."); return
    
    sel_init = st.selectbox("اختر المبادرة", my_data['Mabadara'].unique())
    acts = my_data[my_data['Mabadara']==sel_init]
    
    if not acts.empty:
        sel_act = st.selectbox("النشاط المُراد تحديثه:", acts['Activity'].unique())
        row = acts[acts['Activity']==sel_act].iloc[0]
        
        if str(row.get('Admin_Comment','')).strip():
            st.markdown(f"<div class='admin-alert-box'>📢 <strong>توجيهات المدير:</strong><div class='history-box'>{row['Admin_Comment']}</div></div>", unsafe_allow_html=True)
        
        with st.form("upd_form"):
            c1,c2,c3 = st.columns(3)
            with c1: ns2 = st.date_input("تاريخ البداية", value=parse_date(row['Start_Date']))
            with c2: ne2 = st.date_input("تاريخ النهاية", value=parse_date(row['End_Date']))
            with c3: np2 = st.number_input("نسبة الإنجاز %", min_value=0, max_value=100, value=safe_int(row['Progress']))
            
            el = st.text_input("رابط الدليل (URL)", value=str(row['Evidence_Link']))
            st.write("📜 **ملاحظاتك السابقة:**")
            if str(row['Owner_Comment']): st.markdown(f"<div class='history-box'>{row['Owner_Comment']}</div>", unsafe_allow_html=True)
            nn2 = st.text_area("✍️ أضف تحديثاً أو رداً للمدير")
            
            if st.form_submit_button("💾 حفظ التحديثات"):
                df_save = load_activities_data().copy()
                mask = (df_save['Mabadara']==sel_init) & (df_save['Activity']==sel_act)
                df_save.loc[mask,'Progress'] = int(np2)
                df_save.loc[mask,'Start_Date'] = str(ns2)
                df_save.loc[mask,'End_Date'] = str(ne2)
                df_save.loc[mask,'Evidence_Link'] = str(el)
                if nn2.strip(): df_save.loc[mask,'Owner_Comment'] = append_timestamped_comment(row['Owner_Comment'], nn2)
                
                get_sheet_connection().worksheet("Activities").update(values=[clean_df_for_gspread(df_save).columns.tolist()] + clean_df_for_gspread(df_save).values.tolist(), range_name='A1')
                load_activities_data.clear() # تفريغ الكاش
                st.success("✅ تم تحديث النشاط بنجاح!"); time.sleep(1); st.rerun()

# ---------------------------------------------------------
# 12. التشغيل الرئيسي
# ---------------------------------------------------------
if not st.session_state['logged_in']:
    login()
else:
    with st.container():
        ci, cl = st.columns([8, 1])
        with ci: st.markdown(f"### 👤 {st.session_state['user_info']['name']} | <small>{st.session_state['user_info']['role']}</small>", unsafe_allow_html=True)
        with cl:
            if st.button("تسجيل الخروج"): st.session_state['logged_in'] = False; st.rerun()
    st.write("---")
    
    role = str(st.session_state['user_info']['role']).strip().title()
    if role == 'Admin': admin_view(st.session_state['user_info']['name'])
    elif role == 'Owner': owner_view(st.session_state['user_info']['name'], st.session_state['user_info'].get('assigned_initiative', ''))
    else: st.info("نسخة للاطلاع فقط.")

st.markdown('<div class="footer">System Version: 35.1 (Optimized Dashboard)</div>', unsafe_allow_html=True)
