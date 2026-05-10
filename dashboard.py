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
    .alert-summary-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin-bottom: 20px; }
    .alert-summary-card { border-radius: 10px; padding: 16px; text-align: center; }
    .alert-summary-card .num { font-size: 32px; font-weight: 900; line-height: 1; }
    .alert-summary-card .lbl { font-size: 13px; margin-top: 4px; opacity: .85; }
    .s-red    { background: #fde8e8; color: #c0392b; }
    .s-orange { background: #fef3cd; color: #d35400; }
    .s-blue   { background: #e8f4fd; color: #1a5276; }
    .s-gray   { background: #f3f3f3; color: #2c3e50; }
    .alert-header { display: flex; align-items: center; gap: 10px; padding: 14px 18px;
        border-radius: 10px; margin-bottom: 8px; font-weight: bold; direction: rtl; }
    .alert-overdue { background: #fde8e8; border-right: 5px solid #c0392b; color: #7b241c; }
    .alert-at-risk { background: #fef3cd; border-right: 5px solid #e67e22; color: #784212; }
    .all-good { background: #eafaf1; border-right: 5px solid #27ae60; border-radius: 8px;
        padding: 12px 18px; color: #1e8449; font-weight: bold; margin-bottom: 10px; direction: rtl; }
    .trend-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
        padding: 14px 18px; margin-bottom: 12px; }
    .snapshot-info { background: #f0f4ff; border-radius: 8px; padding: 10px 16px;
        border-right: 4px solid #3498db; margin-bottom: 12px; font-size: 14px; }
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
    .health-card { border-radius: 12px; padding: 16px 20px; margin-bottom: 10px;
        display: flex; align-items: center; gap: 14px; direction: rtl; }
    .health-score { font-size: 36px; font-weight: 900; min-width: 60px; text-align: center; }
    .health-label { font-size: 14px; font-weight: bold; margin-bottom: 2px; }
    .health-detail { font-size: 12px; opacity: .8; }
    .health-green  { background: #eafaf1; border-right: 5px solid #27ae60; color: #1e8449; }
    .health-yellow { background: #fef9e7; border-right: 5px solid #f39c12; color: #7d6608; }
    .health-red    { background: #fde8e8; border-right: 5px solid #e74c3c; color: #7b241c; }
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
SHEET_ID          = "11tKfYa-Sqa96wDwQvMvChgRWaxgMRAWAIvul7p27ayY"
KPI_HISTORY_SHEET = "KPI_History"

def get_creds():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    try:
        if st.secrets is not None and "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception:
        pass
    if os.path.exists("credentials.json"):
        return ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    st.error("خطأ في الاتصال: لم يتم العثور على ملف الاعتمادات.")
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
        if str(val).strip() == "":
            return 0
        return int(float(str(val).replace("%", "").strip()))
    except:
        return 0

def safe_float(val):
    try:
        if str(val).strip() == "":
            return 0.0
        return float(str(val).replace("%", "").strip())
    except:
        return 0.0

def clean_df_for_gspread(df):
    df_clean = df.fillna("")
    return df_clean.astype(object).where(pd.notnull(df_clean), "")

def parse_date(date_str):
    try:
        return pd.to_datetime(date_str).date()
    except:
        return datetime.today().date()

def append_timestamped_comment(original_text, new_comment):
    if not new_comment or str(new_comment).strip() == "":
        return original_text
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = "📅 " + timestamp + ": " + str(new_comment).strip()
    if original_text and str(original_text).strip() != "":
        return str(original_text) + "\n----------------\n" + new_entry
    return new_entry

def _last_update_date(comment_text):
    if not comment_text or str(comment_text).strip() == "":
        return None
    dates = re.findall(r"(\d{4}-\d{2}-\d{2})", str(comment_text))
    if not dates:
        return None
    try:
        return datetime.strptime(dates[-1], "%Y-%m-%d").date()
    except:
        return None

def _parse_end_date(val):
    try:
        return pd.to_datetime(str(val)).date()
    except:
        return None

# ---------------------------------------------------------
# 5. صحة المبادرة (Health Score)
# ---------------------------------------------------------
def calc_initiative_health(df_acts_group):
    today = date.today()
    rows  = df_acts_group
    if rows.empty:
        return {"score": 0, "grade": "غير معروف", "color_class": "health-gray",
                "details": {"progress": 0, "timeliness": 0, "updates": 0}}
    total = len(rows)

    avg_progress   = rows["Progress"].apply(safe_int).mean()
    score_progress = avg_progress

    on_time = 0
    for _, r in rows.iterrows():
        prog = safe_int(r.get("Progress", 0))
        end  = _parse_end_date(r.get("End_Date", ""))
        if prog >= 100:
            on_time += 1
        elif end and end >= today:
            on_time += 1
    score_timeliness = (on_time / total) * 100

    updated_recently = 0
    for _, r in rows.iterrows():
        oc = str(r.get("Owner_Comment", "")).strip()
        lu = _last_update_date(oc)
        if lu and (today - lu).days <= 21:
            updated_recently += 1
        elif safe_int(r.get("Progress", 0)) >= 100:
            updated_recently += 1
    score_updates = (updated_recently / total) * 100

    final_score = round(score_progress * 0.40 +
                        score_timeliness * 0.40 +
                        score_updates    * 0.20)

    if final_score >= 70:
        grade, color_class = "جيد", "health-green"
    elif final_score >= 40:
        grade, color_class = "متوسط", "health-yellow"
    else:
        grade, color_class = "يحتاج متابعة", "health-red"

    return {
        "score": final_score,
        "grade": grade,
        "color_class": color_class,
        "details": {
            "progress":   round(score_progress),
            "timeliness": round(score_timeliness),
            "updates":    round(score_updates),
        },
    }

def _render_health_card(init_name, h):
    score = h["score"]
    grade = h["grade"]
    css   = h["color_class"]
    det   = h["details"]
    short = (init_name[:60] + "…") if len(init_name) > 60 else init_name
    st.markdown(
        "<div class='health-card " + css + "'>"
        "<div class='health-score'>" + str(score) + "</div>"
        "<div>"
        "<div class='health-label'>" + short + "</div>"
        "<div class='health-detail'>"
        "الدرجة: <b>" + grade + "</b> &nbsp;|&nbsp; "
        "الإنجاز: " + str(det["progress"]) + "% &nbsp;|&nbsp; "
        "الالتزام: " + str(det["timeliness"]) + "% &nbsp;|&nbsp; "
        "التحديث: " + str(det["updates"]) + "%"
        "</div></div></div>",
        unsafe_allow_html=True,
    )

def show_health_dashboard(df_acts):
    st.markdown("### 🏥 صحة المبادرات")
    all_initiatives = df_acts["Mabadara"].unique().tolist()
    if not all_initiatives:
        st.info("لا توجد مبادرات.")
        return
    health_data = []
    for init in all_initiatives:
        group  = df_acts[df_acts["Mabadara"] == init].copy()
        result = calc_initiative_health(group)
        health_data.append({"initiative": init, **result})
    health_data.sort(key=lambda x: x["score"], reverse=True)

    green  = sum(1 for h in health_data if h["color_class"] == "health-green")
    yellow = sum(1 for h in health_data if h["color_class"] == "health-yellow")
    red    = sum(1 for h in health_data if h["color_class"] == "health-red")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 إجمالي المبادرات", len(health_data))
    c2.metric("🟢 جيد",             green)
    c3.metric("🟡 متوسط",           yellow)
    c4.metric("🔴 يحتاج متابعة",    red)
    st.markdown("---")

    filter_opt = st.radio(
        "عرض:", ["الكل", "🟢 جيد فقط", "🟡 متوسط فقط", "🔴 يحتاج متابعة فقط"],
        horizontal=True, key="health_filter",
    )
    filter_map = {
        "الكل": None,
        "🟢 جيد فقط": "health-green",
        "🟡 متوسط فقط": "health-yellow",
        "🔴 يحتاج متابعة فقط": "health-red",
    }
    filter_class = filter_map[filter_opt]
    filtered = [h for h in health_data
                if filter_class is None or h["color_class"] == filter_class]
    if not filtered:
        st.info("لا توجد مبادرات في هذه الفئة.")
        return
    for h in filtered:
        _render_health_card(h["initiative"], h)

    st.markdown("#### 📊 مقارنة بصرية")
    names  = [(h["initiative"])[:30] for h in filtered]
    scores = [h["score"] for h in filtered]
    clrs   = []
    for h in filtered:
        if h["color_class"] == "health-green":
            clrs.append("#27ae60")
        elif h["color_class"] == "health-yellow":
            clrs.append("#f39c12")
        else:
            clrs.append("#e74c3c")
    fig = go.Figure(go.Bar(
        x=scores, y=names, orientation="h",
        marker_color=clrs,
        text=[str(s) + "%" for s in scores],
        textposition="outside",
    ))
    fig.update_layout(
        xaxis=dict(range=[0, 110], showgrid=True, gridcolor="#f0f0f0", title="الدرجة"),
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=20, b=20, l=20, r=60),
        height=max(200, len(filtered) * 45),
        showlegend=False,
    )
    fig.add_vline(x=70, line_dash="dash", line_color="#27ae60", annotation_text="جيد 70%")
    fig.add_vline(x=40, line_dash="dash", line_color="#f39c12", annotation_text="متوسط 40%")
    st.plotly_chart(fig, use_container_width=True, key="health_bar_chart")

def show_owner_health(df_acts, my_list):
    my_df = df_acts[df_acts["Mabadara"].isin(my_list)].copy()
    if my_df.empty:
        return
    for init in my_list:
        group  = my_df[my_df["Mabadara"] == init].copy()
        result = calc_initiative_health(group)
        _render_health_card(init, result)

# ---------------------------------------------------------
# 6. نظام المحادثة
# ---------------------------------------------------------
_MSG_PATTERN = re.compile(
    r"📅\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})(?:\s*\[(\w+)\])?:\s*(.*?)(?=📅|\Z)",
    re.DOTALL,
)

def _parse_messages(text, default_role):
    if not text or str(text).strip() == "":
        return []
    msgs = []
    for m in _MSG_PATTERN.finditer(str(text)):
        dt_str = m.group(1).strip()
        role   = (m.group(2) or default_role).strip()
        body   = m.group(3).strip().replace("----------------", "").strip()
        if not body:
            continue
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        except:
            dt = datetime.min
        msgs.append({"dt": dt, "role": role, "text": body})
    return msgs

def _merge_and_sort(owner_text, admin_text):
    return sorted(
        _parse_messages(owner_text, "Owner") + _parse_messages(admin_text, "Admin"),
        key=lambda x: x["dt"],
    )

def _format_new_comment(text, role):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    return "📅 " + ts + " [" + role + "]: " + text.strip()

def _append_comment(original, new_entry):
    original = str(original).strip()
    return (original + "\n" + new_entry) if original else new_entry

def _render_chat(messages):
    if not messages:
        st.markdown(
            "<div class='chat-empty'>💬 لا توجد رسائل بعد — ابدأ المحادثة أدناه</div>",
            unsafe_allow_html=True,
        )
        return
    html      = "<div class='chat-wrap'>"
    prev_date = None
    for msg in messages:
        msg_date = msg["dt"].strftime("%Y-%m-%d")
        if msg_date != prev_date:
            html     += "<div class='chat-divider'>── " + msg_date + " ──</div>"
            prev_date = msg_date
        is_admin = msg["role"] == "Admin"
        cls      = "bubble-admin" if is_admin else "bubble-owner"
        sender   = "المدير" if is_admin else "الموظف"
        time_s   = msg["dt"].strftime("%H:%M")
        text_esc = msg["text"].replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        justify  = "flex-end" if is_admin else "flex-start"
        html += (
            "<div style='display:flex;justify-content:" + justify + "'>"
            "<div class='bubble " + cls + "'>"
            "<div class='meta'>" + sender + " · " + time_s + "</div>"
            + text_esc +
            "</div></div>"
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def _save_chat_msg(ws, df, mask, col_name, new_entry):
    if col_name not in df.columns:
        df[col_name] = ""
    old = str(df.loc[mask, col_name].values[0]).strip()
    df.loc[mask, col_name] = _append_comment(old, new_entry)
    try:
        df_c = clean_df_for_gspread(df)
        ws.update(values=[df_c.columns.tolist()] + df_c.values.tolist(), range_name="A1")
        st.success("✅ تم الإرسال!")
        time.sleep(0.8)
        st.rerun()
    except Exception as e:
        st.error("خطأ: " + str(e))

def show_activity_chat(ws, df_acts, mabadara, activity, current_role, current_user):
    mask = (
        (df_acts["Mabadara"].astype(str).str.strip() == mabadara.strip()) &
        (df_acts["Activity"].astype(str).str.strip()  == activity.strip())
    )
    if not mask.any():
        st.warning("لم يُعثر على النشاط.")
        return
    row      = df_acts[mask].iloc[0]
    messages = _merge_and_sort(str(row.get("Owner_Comment", "")),
                                str(row.get("Admin_Comment", "")))
    short_act = (activity[:55] + "…") if len(activity) > 55 else activity
    st.markdown("#### 💬 محادثة: " + short_act)
    st.caption("المبادرة: " + mabadara[:60])
    c1, c2, c3 = st.columns(3)
    c1.metric("📨 إجمالي الرسائل", len(messages))
    c2.metric("🔵 رسائل المدير",   sum(1 for m in messages if m["role"] == "Admin"))
    c3.metric("🟢 رسائل الموظف",   sum(1 for m in messages if m["role"] == "Owner"))
    st.markdown("---")
    chat_h = min(max(len(messages) * 80, 220), 480)
    with st.container(height=chat_h):
        _render_chat(messages)
    st.markdown("---")
    sender_label = "المدير" if current_role == "Admin" else "الموظف"
    key_in  = "chat_in_"  + mabadara[:12] + "_" + activity[:12]
    key_snd = "chat_snd_" + mabadara[:10] + "_" + activity[:10]
    new_msg = st.text_area(
        "✍️ رسالة جديدة (" + sender_label + ")",
        placeholder="اكتب ردك هنا...", height=90, key=key_in,
    )
    col_s, col_t = st.columns([2, 1])
    with col_s:
        if st.button("📤 إرسال", type="primary", use_container_width=True, key=key_snd):
            if not new_msg.strip():
                st.warning("الرسالة فارغة.")
            else:
                col_name = "Admin_Comment" if current_role == "Admin" else "Owner_Comment"
                _save_chat_msg(ws, df_acts, mask, col_name,
                               _format_new_comment(new_msg, current_role))
    with col_t:
        now_str = datetime.now().strftime("%H:%M")
        st.caption("الوقت: " + now_str)

def show_kpi_chat(ws_kpi, df_kpi, kpi_name, current_role, current_user):
    mask = df_kpi["KPI_Name"].astype(str).str.strip() == kpi_name.strip()
    if not mask.any():
        st.warning("لم يُعثر على المؤشر.")
        return
    row      = df_kpi[mask].iloc[0]
    messages = _merge_and_sort(str(row.get("Owner_Comment", "")),
                                str(row.get("Admin_Comment", "")))
    short_k  = (kpi_name[:55] + "…") if len(kpi_name) > 55 else kpi_name
    st.markdown("#### 💬 محادثة المؤشر: " + short_k)
    c1, c2, c3 = st.columns(3)
    c1.metric("📨 إجمالي", len(messages))
    c2.metric("🔵 المدير",  sum(1 for m in messages if m["role"] == "Admin"))
    c3.metric("🟢 الموظف",  sum(1 for m in messages if m["role"] == "Owner"))
    st.markdown("---")
    chat_h = min(max(len(messages) * 80, 220), 480)
    with st.container(height=chat_h):
        _render_chat(messages)
    st.markdown("---")
    sender_label = "المدير" if current_role == "Admin" else "الموظف"
    key_in  = "kpi_chat_in_"  + kpi_name[:28]
    key_snd = "kpi_chat_snd_" + kpi_name[:23]
    new_msg = st.text_area(
        "✍️ رسالة جديدة (" + sender_label + ")",
        placeholder="اكتب ردك هنا...", height=90, key=key_in,
    )
    if st.button("📤 إرسال", type="primary", use_container_width=True, key=key_snd):
        if not new_msg.strip():
            st.warning("الرسالة فارغة.")
        else:
            col_name = "Admin_Comment" if current_role == "Admin" else "Owner_Comment"
            _save_chat_msg(ws_kpi, df_kpi, mask, col_name,
                           _format_new_comment(new_msg, current_role))

# ---------------------------------------------------------
# 7. نظام التتبع التاريخي
# ---------------------------------------------------------
@st.cache_data(ttl=120, show_spinner=False)
def load_kpi_history(_cache_key):
    COLS  = ["KPI_Name", "Date", "Actual", "Target", "Recorded_By", "Note"]
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
        st.warning("تحذير: تعذّر تحميل السجل التاريخي — " + str(e))
        return empty

def _get_or_create_history_ws(sh):
    try:
        return sh.worksheet(KPI_HISTORY_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=KPI_HISTORY_SHEET, rows=2000, cols=6)
        ws.append_row(["KPI_Name", "Date", "Actual", "Target", "Recorded_By", "Note"])
        return ws

def save_kpi_snapshot(kpi_name, actual, target, recorded_by, note=""):
    today_str = date.today().isoformat()
    try:
        sh   = get_sheet_connection()
        ws   = _get_or_create_history_ws(sh)
        recs = ws.get_all_records()
        for i, r in enumerate(recs):
            if (str(r.get("KPI_Name", "")).strip() == kpi_name.strip()
                    and str(r.get("Date", "")).strip() == today_str):
                row_ref = "A" + str(i + 2) + ":F" + str(i + 2)
                ws.update(row_ref, [[kpi_name, today_str, actual, target, recorded_by, note]])
                load_kpi_history.clear()
                return True
        ws.append_row([kpi_name, today_str, actual, target, recorded_by, note])
        load_kpi_history.clear()
        return True
    except Exception as e:
        st.error("خطأ في حفظ السجل التاريخي: " + str(e))
        return False

def save_all_kpis_snapshot(df_kpi, recorded_by):
    today_str = date.today().isoformat()
    try:
        sh        = get_sheet_connection()
        ws        = _get_or_create_history_ws(sh)
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
            ref = "A" + str(row_idx) + ":F" + str(row_idx)
            ws.update(ref, [data])
        if new_rows:
            ws.append_rows(new_rows, value_input_option="USER_ENTERED")
        load_kpi_history.clear()
        return len(new_rows) + len(update_ops)
    except Exception as e:
        st.error("خطأ في اللقطة الشاملة: " + str(e))
        return 0

def compute_trend(series):
    vals = series.dropna().tolist()
    if len(vals) < 2:
        return {"direction": "flat", "pct": 0.0,
                "label": "لا يوجد سجل كافٍ", "css": "trend-flat", "icon": "➖"}
    last, prev = vals[-1], vals[-2]
    pct = ((last - prev) / abs(prev) * 100) if prev != 0 else (100.0 if last > 0 else 0.0)
    if pct > 2:
        return {"direction": "up",   "pct": pct,
                "label": "▲ " + str(round(pct, 1)) + "%", "css": "trend-up", "icon": "▲"}
    elif pct < -2:
        return {"direction": "down", "pct": pct,
                "label": "▼ " + str(round(abs(pct), 1)) + "%", "css": "trend-down", "icon": "▼"}
    else:
        return {"direction": "flat", "pct": pct,
                "label": "مستقر ➖", "css": "trend-flat", "icon": "➖"}

def plot_kpi_trend(df_history, kpi_name, direction="تصاعدي", unit="", ctx=""):
    df = df_history[
        df_history["KPI_Name"].astype(str).str.strip() == kpi_name.strip()
    ].copy().sort_values("Date")
    if df.empty:
        st.info("لا توجد بيانات تاريخية بعد.")
        return
    trend = compute_trend(df["Actual"])
    if direction == "تنازلي":
        lc = "#27ae60" if trend["direction"] == "down" else (
             "#e74c3c" if trend["direction"] == "up" else "#3498db")
    else:
        lc = "#27ae60" if trend["direction"] == "up" else (
             "#e74c3c" if trend["direction"] == "down" else "#3498db")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Target"], mode="lines", name="المستهدف",
        line=dict(color="#e67e22", width=2, dash="dot"),
        hovertemplate="المستهدف: %{y}<extra></extra>",
    ))
    act_texts = [str(round(float(v), 1)) for v in df["Actual"]]
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Actual"], mode="lines+markers+text", name="الفعلي",
        line=dict(color=lc, width=3),
        marker=dict(size=8, color=lc, line=dict(color="white", width=2)),
        text=act_texts, textposition="top center",
        textfont=dict(size=11, color=lc),
        hovertemplate="<b>%{x|%Y-%m-%d}</b><br>الفعلي: %{y}<extra></extra>",
    ))
    last     = df.iloc[-1]
    last_val = str(round(float(last["Actual"]), 1))
    fig.add_trace(go.Scatter(
        x=[last["Date"]], y=[last["Actual"]], mode="markers", showlegend=False,
        marker=dict(size=15, color=lc, line=dict(color="white", width=3), symbol="circle"),
        hovertemplate="آخر قيمة: " + last_val + "<extra></extra>",
    ))
    chart_title = "<b>" + kpi_name[:45] + "</b>   " + trend["label"]
    fig.update_layout(
        title=dict(text=chart_title, x=0.5, xanchor="center", font=dict(size=13)),
        xaxis=dict(title="", showgrid=True, gridcolor="#f0f0f0", tickformat="%b %Y"),
        yaxis=dict(title=unit or "القيمة", showgrid=True, gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=70, b=30, l=40, r=20), height=300,
        hovermode="x unified",
    )
    safe_key = (kpi_name + ctx).replace(" ", "_").replace("/", "_").replace("-", "_")[:80]
    st.plotly_chart(fig, use_container_width=True, key="trend_" + safe_key)
    with st.expander("📋 جدول البيانات التاريخية"):
        show = df[["Date", "Actual", "Target", "Recorded_By", "Note"]].copy()
        show["Date"] = show["Date"].dt.strftime("%Y-%m-%d")
        show.columns = ["التاريخ", "الفعلي", "المستهدف", "سجّل بواسطة", "ملاحظة"]
        st.dataframe(show.sort_values("التاريخ", ascending=False),
                     hide_index=True, use_container_width=True)

def show_history_overview(df_history, df_kpi):
    if df_history.empty:
        st.markdown(
            "<div class='snapshot-info'>📌 لا يوجد سجل تاريخي بعد — "
            "اضغط <b>تسجيل لقطة شاملة</b> لبدء التتبع.</div>",
            unsafe_allow_html=True,
        )
        return
    cats = ["الكل"] + list(KPI_GROUPS.keys())
    sel  = st.selectbox("عرض مجموعة:", cats, key="ov_cat")
    recorded = df_history["KPI_Name"].astype(str).str.strip().unique().tolist()
    kpis = recorded if sel == "الكل" else [
        k for k in KPI_GROUPS.get(sel, []) if k in recorded
    ]
    if not kpis:
        st.info("لا توجد بيانات تاريخية للمجموعة المختارة بعد.")
        return
    cols = st.columns(2)
    for i, kpi in enumerate(kpis):
        ki   = df_kpi[df_kpi["KPI_Name"].astype(str).str.strip() == kpi.strip()]
        unit = ki["Unit"].values[0]      if not ki.empty and "Unit"      in ki.columns else ""
        drx  = ki["Direction"].values[0] if not ki.empty and "Direction" in ki.columns else "تصاعدي"
        kh   = df_history[
            df_history["KPI_Name"].astype(str).str.strip() == kpi.strip()
        ].sort_values("Date")
        trend    = compute_trend(kh["Actual"])
        last_val = str(round(float(kh["Actual"].iloc[-1]), 1))
        with cols[i % 2]:
            st.markdown(
                "<div class='trend-card'>"
                "<b>" + kpi[:55] + "</b><br>"
                "<span class='" + trend["css"] + "'>" + trend["label"] + "</span>"
                " &nbsp;|&nbsp; آخر قيمة: <b>" + last_val + "</b>"
                "</div>",
                unsafe_allow_html=True,
            )
            plot_kpi_trend(df_history, kpi, drx, unit, ctx="_ov")


# ---------------------------------------------------------
# دوال التتبع التاريخي للمؤشرات التشغيلية
# ---------------------------------------------------------
OPS_HISTORY_SHEET = "Ops_KPI_History"

@st.cache_data(ttl=120, show_spinner=False)
def load_ops_history(_key):
    COLS = ["KPI_Name", "Date", "Actual", "Target", "Recorded_By", "Note"]
    empty = pd.DataFrame(columns=COLS)
    try:
        sh2 = get_sheet_connection()
        try:
            ws = sh2.worksheet(OPS_HISTORY_SHEET)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh2.add_worksheet(title=OPS_HISTORY_SHEET, rows=2000, cols=6)
            ws.append_row(COLS)
            return empty
        recs = ws.get_all_records()
        if not recs:
            return empty
        df = pd.DataFrame(recs)
        df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
        df["Actual"] = df["Actual"].apply(safe_float)
        df["Target"] = df["Target"].apply(safe_float)
        return df.dropna(subset=["Date"])
    except Exception as e:
        st.warning("تحذير تاريخ تشغيلي: " + str(e))
        return empty

def save_ops_snapshot(kpi_name, actual, target, recorded_by, note=""):
    today_str = date.today().isoformat()
    try:
        sh2 = get_sheet_connection()
        try:
            ws = sh2.worksheet(OPS_HISTORY_SHEET)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh2.add_worksheet(title=OPS_HISTORY_SHEET, rows=2000, cols=6)
            ws.append_row(["KPI_Name","Date","Actual","Target","Recorded_By","Note"])
        recs = ws.get_all_records()
        for i, r in enumerate(recs):
            if (str(r.get("KPI_Name","")).strip() == kpi_name.strip()
                    and str(r.get("Date","")).strip() == today_str):
                ws.update("A" + str(i+2) + ":F" + str(i+2),
                          [[kpi_name, today_str, actual, target, recorded_by, note]])
                load_ops_history.clear()
                return True
        ws.append_row([kpi_name, today_str, actual, target, recorded_by, note])
        load_ops_history.clear()
        return True
    except Exception as e:
        st.error("خطأ في حفظ التاريخ التشغيلي: " + str(e))
        return False

def plot_ops_trend(df_hist, kpi_name, direction="تصاعدي", ctx=""):
    df = df_hist[
        df_hist["KPI_Name"].astype(str).str.strip() == kpi_name.strip()
    ].copy().sort_values("Date")
    if df.empty:
        st.info("لا توجد بيانات تاريخية بعد لهذا المؤشر.")
        return
    trend = compute_trend(df["Actual"])
    if direction == "تنازلي":
        lc = "#27ae60" if trend["direction"] == "down" else (
             "#e74c3c" if trend["direction"] == "up" else "#3498db")
    else:
        lc = "#27ae60" if trend["direction"] == "up" else (
             "#e74c3c" if trend["direction"] == "down" else "#3498db")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Target"], mode="lines", name="المستهدف",
        line=dict(color="#e67e22", width=2, dash="dot"),
        hovertemplate="المستهدف: %{y}<extra></extra>",
    ))
    act_texts = [str(round(float(v), 2)) for v in df["Actual"]]
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Actual"], mode="lines+markers+text", name="الفعلي",
        line=dict(color=lc, width=3),
        marker=dict(size=8, color=lc, line=dict(color="white", width=2)),
        text=act_texts, textposition="top center",
        textfont=dict(size=11, color=lc),
        hovertemplate="<b>%{x|%Y-%m-%d}</b><br>الفعلي: %{y}<extra></extra>",
    ))
    last     = df.iloc[-1]
    last_val = str(round(float(last["Actual"]), 2))
    fig.add_trace(go.Scatter(
        x=[last["Date"]], y=[last["Actual"]], mode="markers", showlegend=False,
        marker=dict(size=14, color=lc, line=dict(color="white", width=3)),
        hovertemplate="آخر قيمة: " + last_val + "<extra></extra>",
    ))
    chart_title = "<b>" + kpi_name[:50] + "</b>   " + trend["label"]
    fig.update_layout(
        title=dict(text=chart_title, x=0.5, xanchor="center", font=dict(size=13)),
        xaxis=dict(title="", showgrid=True, gridcolor="#f0f0f0", tickformat="%b %Y"),
        yaxis=dict(title="القيمة", showgrid=True, gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=70, b=30, l=40, r=20), height=290,
        hovermode="x unified",
    )
    safe_key = (kpi_name + ctx).replace(" ","_").replace("/","_").replace("-","_")[:80]
    st.plotly_chart(fig, use_container_width=True, key="ops_trend_" + safe_key)
    with st.expander("📋 جدول البيانات التاريخية"):
        show = df[["Date","Actual","Target","Recorded_By","Note"]].copy()
        show["Date"] = show["Date"].dt.strftime("%Y-%m-%d")
        show.columns = ["التاريخ","الفعلي","المستهدف","سجّل بواسطة","ملاحظة"]
        st.dataframe(show.sort_values("التاريخ", ascending=False),
                     hide_index=True, use_container_width=True)

# ---------------------------------------------------------
# 8. محرك التنبيهات
# ---------------------------------------------------------
def analyze_activities(df):
    today  = date.today()
    result = {"overdue": [], "at_risk": [], "stale": [], "no_comment": []}
    for _, row in df.iterrows():
        mab  = str(row.get("Mabadara", "")).strip()
        act  = str(row.get("Activity",  "")).strip()
        smab = (mab[:30] + "…") if len(mab) > 30 else mab
        sact = (act[:45] + "…") if len(act) > 45 else act
        prog = safe_int(row.get("Progress", 0))
        end  = _parse_end_date(row.get("End_Date", ""))
        oc   = str(row.get("Owner_Comment", "")).strip()
        dl   = (end - today).days if end else None
        do_  = (today - end).days  if end else None
        base = {"مبادرة": smab, "النشاط": sact, "الإنجاز": prog}
        if end and prog < 100 and end < today:
            result["overdue"].append({**base, "تاريخ الانتهاء": str(end), "أيام التأخير": do_})
        elif end and dl is not None and 0 <= dl <= 14 and prog < 80:
            result["at_risk"].append({**base, "تاريخ الانتهاء": str(end), "أيام متبقية": dl})
        lu = _last_update_date(oc)
        if lu and (today - lu).days > 21:
            result["stale"].append({**base, "آخر تحديث": str(lu),
                                    "أيام منذ التحديث": (today - lu).days})
        if not oc and prog < 100:
            result["no_comment"].append({**base})
    return result

def analyze_kpis_alerts(df_kpi):
    alerts = []
    today  = date.today()
    for _, row in df_kpi.iterrows():
        kpi  = str(row.get("KPI_Name", "")).strip()
        own  = str(row.get("Owner", "")).strip()
        tgt  = safe_float(row.get("Target", 0))
        act  = safe_float(row.get("Actual", 0))
        cmt  = str(row.get("Owner_Comment", "")).strip()
        drx  = str(row.get("Direction", "تصاعدي")).strip()
        reas = []
        if drx == "تصاعدي":
            if tgt > 0 and act == 0:
                reas.append("المتحقق = 0")
            elif tgt > 0 and (act / tgt) < 0.5:
                reas.append("المتحقق " + str(round((act / tgt) * 100)) + "% من المستهدف")
        else:
            if act > tgt * 1.5 and tgt > 0:
                reas.append("تجاوز الحد الأعلى")
        lu = _last_update_date(cmt)
        if lu and (today - lu).days > 30:
            reas.append("لم يُحدَّث منذ " + str((today - lu).days) + " يوماً")
        elif not cmt:
            reas.append("لا يوجد تعليق")
        if reas:
            ks = (kpi[:40] + "…") if len(kpi) > 40 else kpi
            alerts.append({"المؤشر": ks, "المسؤول": own,
                           "المستهدف": tgt, "المتحقق": act, "السبب": " | ".join(reas)})
    return alerts

def show_alerts_panel(df_acts, df_kpi=None):
    alerts     = analyze_activities(df_acts)
    total_acts = sum(len(v) for v in alerts.values())
    kpi_alerts = analyze_kpis_alerts(df_kpi) if df_kpi is not None else []
    st.markdown("## 🔔 مركز التنبيهات")
    if total_acts == 0 and not kpi_alerts:
        st.markdown(
            "<div class='all-good'>✅ لا توجد تنبيهات — جميع الأنشطة والمؤشرات على المسار الصحيح</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        return
    ov_n = len(alerts["overdue"])
    ar_n = len(alerts["at_risk"])
    st_n = len(alerts["stale"])
    nc_n = len(alerts["no_comment"])
    st.markdown(
        "<div class='alert-summary-grid'>"
        "<div class='alert-summary-card s-red'><div class='num'>" + str(ov_n) +
        "</div><div class='lbl'>🚨 متأخرة</div></div>"
        "<div class='alert-summary-card s-orange'><div class='num'>" + str(ar_n) +
        "</div><div class='lbl'>⚠️ في خطر (14 يوم)</div></div>"
        "<div class='alert-summary-card s-blue'><div class='num'>" + str(st_n) +
        "</div><div class='lbl'>🕐 لم تُحدَّث (21 يوم)</div></div>"
        "<div class='alert-summary-card s-gray'><div class='num'>" + str(nc_n) +
        "</div><div class='lbl'>📭 بدون تعليق</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    with st.expander("🚨 الأنشطة المتأخرة (" + str(ov_n) + ")", expanded=bool(alerts["overdue"])):
        if alerts["overdue"]:
            st.dataframe(
                pd.DataFrame(alerts["overdue"]).sort_values("أيام التأخير", ascending=False),
                hide_index=True, use_container_width=True,
                column_config={
                    "الإنجاز": st.column_config.ProgressColumn("الإنجاز %", format="%d%%", min_value=0, max_value=100),
                    "أيام التأخير": st.column_config.NumberColumn(format="%d يوم"),
                },
            )
        else:
            st.markdown("<div class='all-good'>✅ لا توجد أنشطة متأخرة</div>", unsafe_allow_html=True)
    with st.expander("⚠️ في خطر (" + str(ar_n) + ")"):
        if alerts["at_risk"]:
            st.dataframe(
                pd.DataFrame(alerts["at_risk"]), hide_index=True, use_container_width=True,
                column_config={
                    "الإنجاز": st.column_config.ProgressColumn("الإنجاز %", format="%d%%", min_value=0, max_value=100),
                    "أيام متبقية": st.column_config.NumberColumn(format="%d يوم"),
                },
            )
        else:
            st.markdown("<div class='all-good'>✅ لا توجد أنشطة في خطر قريب</div>", unsafe_allow_html=True)
    with st.expander("🕐 لم تُحدَّث منذ أكثر من 21 يوماً (" + str(st_n) + ")"):
        if alerts["stale"]:
            st.dataframe(
                pd.DataFrame(alerts["stale"]).sort_values("أيام منذ التحديث", ascending=False),
                hide_index=True, use_container_width=True,
                column_config={"أيام منذ التحديث": st.column_config.NumberColumn(format="%d يوم")},
            )
        else:
            st.markdown("<div class='all-good'>✅ جميع الأنشطة تُحدَّث بانتظام</div>", unsafe_allow_html=True)
    with st.expander("📭 بدون تعليق (" + str(nc_n) + ")"):
        if alerts["no_comment"]:
            st.dataframe(pd.DataFrame(alerts["no_comment"]), hide_index=True, use_container_width=True)
        else:
            st.markdown("<div class='all-good'>✅ جميع الأنشطة لديها تعليقات</div>", unsafe_allow_html=True)
    if df_kpi is not None:
        kpi_n = len(kpi_alerts)
        with st.expander("📊 تنبيهات مؤشرات الأداء (" + str(kpi_n) + ")"):
            if kpi_alerts:
                st.dataframe(pd.DataFrame(kpi_alerts), hide_index=True, use_container_width=True)
            else:
                st.markdown("<div class='all-good'>✅ جميع المؤشرات ضمن النطاق</div>", unsafe_allow_html=True)
    st.markdown("---")

def show_owner_alerts(df_acts, my_list):
    my_df  = df_acts[df_acts["Mabadara"].isin(my_list)].copy()
    if my_df.empty:
        return
    alerts = analyze_activities(my_df)
    if alerts["overdue"]:
        n = len(alerts["overdue"])
        st.markdown(
            "<div class='alert-header alert-overdue'>🚨 لديك <strong>" + str(n) +
            "</strong> نشاط متأخر يحتاج تحديثاً فورياً</div>",
            unsafe_allow_html=True,
        )
    if alerts["at_risk"]:
        n = len(alerts["at_risk"])
        st.markdown(
            "<div class='alert-header alert-at-risk'>⚠️ لديك <strong>" + str(n) +
            "</strong> نشاط ينتهي خلال 14 يوماً وإنجازه أقل من 80%</div>",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------
# 9. تسجيل الدخول
# ---------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_info"] = {}

def login():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h2 style='text-align:center;'>🔐 تسجيل الدخول</h2>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("دخول", use_container_width=True):
            try:
                sh       = get_sheet_connection()
                users_df = pd.DataFrame(sh.worksheet("Users").get_all_records())
                users_df["username"] = users_df["username"].astype(str).str.strip()
                user = users_df[users_df["username"] == username.strip()]
                if not user.empty and str(user.iloc[0]["password"]) == str(password):
                    st.session_state["logged_in"] = True
                    st.session_state["user_info"] = user.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("بيانات الدخول غير صحيحة")
            except Exception as e:
                st.error("خطأ اتصال: " + str(e))

# ---------------------------------------------------------
# 10. رسم Bar Chart
# ---------------------------------------------------------
def plot_group_barchart(df, group_title, ctx=""):
    if df.empty:
        st.info("لا توجد مؤشرات في: " + group_title)
        return

    def get_color(row):
        t = row["Target"]
        a = row["Actual"]
        d = str(row.get("Direction", "تصاعدي")).strip()
        if d == "تنازلي":
            return "#2ca02c" if a <= t else "#d62728"
        return "#1f77b4" if a > t else ("#2ca02c" if a == t else "#d62728")

    df = df.copy()
    df["Color"] = df.apply(get_color, axis=1)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["KPI_Name"], y=df["Actual"], name="الفعلي",
        marker_color=df["Color"], text=df["Actual"], textposition="auto", width=0.6,
    ))
    fig.add_trace(go.Scatter(
        x=df["KPI_Name"], y=df["Target"], mode="markers", name="المستهدف",
        marker=dict(symbol="line-ew", size=40, color="black", line=dict(width=3)),
    ))
    fig.update_layout(
        title=dict(text="📊 " + group_title, x=0.5, xanchor="center"),
        barmode="overlay", bargap=0.4,
        yaxis=dict(showgrid=True, gridcolor="lightgrey"),
        margin=dict(t=80, b=50, l=20, r=20),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
    )
    sk = (group_title + ctx).replace(" ", "_").replace("/", "_")[:80]
    st.plotly_chart(fig, use_container_width=True, key="bar_" + sk)

def display_kpi_layout(df_all, ctx=""):
    df_all = df_all.copy()
    df_all["Category"] = df_all["KPI_Name"].apply(get_kpi_category)
    c1, c2 = st.columns(2)
    with c1:
        plot_group_barchart(df_all[df_all["Category"] == "QI4SD"],
                            "مجموعة QI4SD", ctx)
    with c2:
        plot_group_barchart(df_all[df_all["Category"] == "البحث والتطوير"],
                            "مجموعة البحث والتطوير", ctx)
    st.markdown("---")
    plot_group_barchart(df_all[df_all["Category"] == "الكفاءة التشغيلية"],
                        "مجموعة الكفاءة التشغيلية", ctx)

# ---------------------------------------------------------
# 11. واجهة المدير
# ---------------------------------------------------------
def admin_view(sh, user_name):
    st.markdown("### 📊 لوحة القيادة التنفيذية")

    try:
        ws_acts = sh.worksheet("Activities")
        df_acts = pd.DataFrame(ws_acts.get_all_records())
        df_acts["Progress"] = df_acts["Progress"].apply(safe_int)
    except Exception as e:
        st.error("خطأ في تحميل الأنشطة: " + str(e))
        return

    try:
        ws_kpi = sh.worksheet("KPIs")
        df_kpi = pd.DataFrame(ws_kpi.get_all_records())
        for c in ["Admin_Comment", "Owner_Comment", "Owner"]:
            if c not in df_kpi.columns:
                df_kpi[c] = ""
        df_kpi["Target"] = df_kpi["Target"].apply(safe_float)
        df_kpi["Actual"] = df_kpi["Actual"].apply(safe_float)
    except Exception as e:
        st.error("خطأ في تحميل المؤشرات: " + str(e))
        df_kpi = None

    if not df_acts.empty:
        today_dt = datetime.now().date()
        df_acts["_end"] = pd.to_datetime(df_acts["End_Date"], errors="coerce").dt.date
        delayed_n = len(df_acts[
            (df_acts["Progress"] < 100) &
            (df_acts["_end"].notna()) &
            (df_acts["_end"] < today_dt)
        ])

    show_alerts_panel(df_acts, df_kpi)

    view = st.selectbox(
        "القسم:",
        ["📋 تفاصيل المبادرات", "📊 مؤشرات الأداء", "⚙️ المؤشرات التشغيلية", "🏥 صحة المبادرات", "📈 التتبع التاريخي", "📷 تسجيل لقطة شاملة", "📄 تصدير PDF", "💬 المحادثات"],
        key="admin_view_select",
    )
    st.markdown("---")

    if view == "📋 تفاصيل المبادرات":
        try:
            if "Admin_Comment" not in df_acts.columns:
                df_acts["Admin_Comment"] = ""
            st.markdown("#### 🔎 مراجعة وتحديث المبادرات")
            st.caption("أضف ملاحظة في عمود 'ملاحظة إدارية جديدة' ثم اضغط حفظ.")
            init    = st.selectbox("اختر المبادرة:", df_acts["Mabadara"].unique())
            df_filt = df_acts[df_acts["Mabadara"] == init].copy()
            df_filt["New_Admin_Note"] = ""
            edited  = st.data_editor(
                df_filt,
                column_config={
                    "Activity":       st.column_config.TextColumn("النشاط", width="large"),
                    "Progress":       st.column_config.ProgressColumn("الإنجاز %", format="%d%%", min_value=0, max_value=100),
                    "Start_Date":     st.column_config.DateColumn("تاريخ البداية", format="YYYY-MM-DD"),
                    "End_Date":       st.column_config.DateColumn("تاريخ النهاية", format="YYYY-MM-DD"),
                    "Owner_Comment":  st.column_config.TextColumn("رد الموظف", width="medium"),
                    "Admin_Comment":  st.column_config.TextColumn("سجل المدير", width="medium"),
                    "New_Admin_Note": st.column_config.TextColumn("✍️ ملاحظة إدارية جديدة", width="large"),
                    "Evidence_Link":  st.column_config.LinkColumn("رابط الدليل", display_text="📎 فتح"),
                    "_end": None, "Mabadara": None,
                },
                disabled=["Activity", "Progress", "Owner_Comment", "Admin_Comment",
                          "Mabadara", "Start_Date", "End_Date"],
                hide_index=True, use_container_width=True,
                key="admin_acts_ed", num_rows="fixed",
            )
            if st.button("💾 حفظ الملاحظات (أنشطة)"):
                with st.spinner("جاري الحفظ..."):
                    df_save = df_acts.drop(columns=["_end"], errors="ignore")
                    changed = False
                    for _, row in edited.iterrows():
                        nn = str(row["New_Admin_Note"]).strip()
                        if nn:
                            changed = True
                            mask = (
                                (df_save["Mabadara"] == row["Mabadara"]) &
                                (df_save["Activity"] == row["Activity"])
                            )
                            if mask.any():
                                old_note = df_save.loc[mask, "Admin_Comment"].values[0]
                                df_save.loc[mask, "Admin_Comment"] = \
                                    append_timestamped_comment(old_note, nn)
                    if changed:
                        cdf = clean_df_for_gspread(df_save)
                        ws_acts.update(
                            values=[cdf.columns.tolist()] + cdf.values.tolist(),
                            range_name="A1",
                        )
                        st.success("✅ تم الحفظ!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.info("لم تُكتب أي ملاحظات.")

            st.markdown("---")
            st.markdown("##### 📜 السجل التاريخي للنشاط")
            sel_act = st.selectbox("اختر النشاط:", df_filt["Activity"].unique(), key="hist_act")
            if sel_act:
                r   = df_filt[df_filt["Activity"] == sel_act].iloc[0]
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("<div class='history-title'>تعليقات الموظف:</div>",
                                unsafe_allow_html=True)
                    oc_val = str(r.get("Owner_Comment", "لا يوجد"))
                    st.markdown("<div class='history-box'>" + oc_val + "</div>",
                                unsafe_allow_html=True)
                with c2:
                    st.markdown("<div class='history-title'>سجل ملاحظات المدير:</div>",
                                unsafe_allow_html=True)
                    ac_val = str(r.get("Admin_Comment", "لا يوجد"))
                    st.markdown("<div class='history-box'>" + ac_val + "</div>",
                                unsafe_allow_html=True)
        except Exception as e:
            st.error("خطأ: " + str(e))

    elif view == "📊 مؤشرات الأداء":
        if df_kpi is None:
            st.error("تعذّر تحميل المؤشرات.")
        else:
            display_kpi_layout(df_kpi, ctx="_adm_tab2")
            st.markdown("---")
            st.markdown("#### ✏️ تحديث البيانات والملاحظات")
            fc = st.selectbox("📂 فلترة:", ["الكل"] + list(KPI_GROUPS.keys()), key="kpi_filt")
            df_kpi["Category"] = df_kpi["KPI_Name"].apply(get_kpi_category)
            dfe = df_kpi[df_kpi["Category"] == fc].copy() if fc != "الكل" else df_kpi.copy()
            dfe["New_Admin_Note"] = ""
            ek  = st.data_editor(
                dfe, num_rows="fixed", use_container_width=True, key="kpi_ed_adm",
                column_config={
                    "KPI_Name":       st.column_config.TextColumn("المؤشر", width="large"),
                    "Target":         st.column_config.NumberColumn("المستهدف", required=True),
                    "Actual":         st.column_config.NumberColumn("الفعلي"),
                    "Owner":          st.column_config.TextColumn("المسؤول"),
                    "Owner_Comment":  st.column_config.TextColumn("ملاحظات المالك", width="medium"),
                    "Admin_Comment":  st.column_config.TextColumn("سجل المدير", width="medium"),
                    "New_Admin_Note": st.column_config.TextColumn("✍️ ملاحظة جديدة", width="large"),
                    "Category": None, "Unit": None, "Direction": None, "Frequency": None,
                },
                disabled=["KPI_Name", "Actual", "Owner", "Owner_Comment", "Admin_Comment", "Category"],
            )
            if st.button("💾 حفظ تحديثات المؤشرات"):
                with st.spinner("جاري الحفظ..."):
                    changed = False
                    for _, row in ek.iterrows():
                        mask = df_kpi["KPI_Name"] == row["KPI_Name"]
                        if mask.any():
                            if float(row["Target"]) != float(df_kpi.loc[mask, "Target"].values[0]):
                                df_kpi.loc[mask, "Target"] = row["Target"]
                                changed = True
                            nn = str(row["New_Admin_Note"]).strip()
                            if nn:
                                old_note = df_kpi.loc[mask, "Admin_Comment"].values[0]
                                df_kpi.loc[mask, "Admin_Comment"] = \
                                    append_timestamped_comment(old_note, nn)
                                changed = True
                    if changed:
                        cdf = clean_df_for_gspread(df_kpi)
                        ws_kpi.update(
                            values=[cdf.columns.tolist()] + cdf.values.tolist(),
                            range_name="A1",
                        )
                        st.success("✅ تم الحفظ!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.info("لا توجد تغييرات.")
            st.markdown("---")
            st.markdown("##### 📜 سجل المؤشر")
            sk = st.selectbox("اختر المؤشر:", df_kpi["KPI_Name"].unique(), key="hist_kpi")
            if sk:
                rk = df_kpi[df_kpi["KPI_Name"] == sk].iloc[0]
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("<div class='history-title'>سجل المالك:</div>",
                                unsafe_allow_html=True)
                    oc_v = str(rk.get("Owner_Comment", "لا يوجد"))
                    st.markdown("<div class='history-box'>" + oc_v + "</div>",
                                unsafe_allow_html=True)
                with c2:
                    st.markdown("<div class='history-title'>سجل المدير:</div>",
                                unsafe_allow_html=True)
                    ac_v = str(rk.get("Admin_Comment", "لا يوجد"))
                    st.markdown("<div class='history-box'>" + ac_v + "</div>",
                                unsafe_allow_html=True)


    elif view == "⚙️ المؤشرات التشغيلية":
        st.markdown("### ⚙️ مؤشرات العمليات التشغيلية")
        st.caption("تحقيق مستهدفات العمليات التشغيلية — البيانات محفوظة في ورقة Operational_KPIs")

        # ── تحميل البيانات ──
        try:
            ws_ops = sh.worksheet("Operational_KPIs")
            df_ops = pd.DataFrame(ws_ops.get_all_records())
        except Exception:
            # إنشاء الورقة بالبيانات الأولية إن لم تكن موجودة
            try:
                ws_ops = sh.add_worksheet(title="Operational_KPIs", rows=100, cols=8)
                headers = ["رقم المؤشر", "المؤشر", "النوع", "الاتجاه", "المستهدف 2026", "المتحقق", "النسبة", "ملاحظات"]
                initial_data = [
                    [1,  "عدد القياسات/ المعايرات المنفذة",                   "عدد",   "تصاعدي", 5955, 996,  "", ""],
                    [2,  "نسبة المعايرات المنجزة في الوقت المحدد",            "نسبة",  "تصاعدي", 1,    0.97, "", ""],
                    [3,  "الفترة الزمنية المستغرقة لمعايرة/قياس جهاز",       "عدد",   "تنازلي", 5,    11,   "", ""],
                    [4,  "عدد الأجهزة المدروسة",                              "عدد",   "تصاعدي", 7818, 1413, "", ""],
                    [5,  "نسبة جهات تقويم المطابقة المسندة للمركز",          "نسبة",  "تصاعدي", 272,  272,  "", ""],
                    [6,  "عدد الجهات المرتبطة بالوقت الوطني",                "عدد",   "تصاعدي", 13,   26,   "", ""],
                    [7,  "عدد مرات الدخول على نظام الوقت",                   "عدد",   "تصاعدي", 622,  200,  "", ""],
                    [8,  "نسبة انجاز خطة انتاج المواد المرجعية المستهدفة",   "نسبة",  "تصاعدي", 0.9,  0,    "", ""],
                    [9,  "عدد المستفيدين من برامج اختبار الكفاءة الفنية",    "عدد",   "تصاعدي", 147,  52,   "", ""],
                    [10, "عدد برامج الكفاءة الفنية المقدمة",                 "عدد",   "تصاعدي", 185,  12,   "", ""],
                    [11, "عدد تقارير الكفاءة الفنية الصادرة",                "عدد",   "تصاعدي", 79,   18,   "", ""],
                ]
                ws_ops.update(values=[headers] + initial_data, range_name="A1")
                df_ops = pd.DataFrame(initial_data, columns=headers)
                st.success("✅ تم إنشاء ورقة Operational_KPIs وتعبئتها بالبيانات الأولية.")
            except Exception as e2:
                st.error("خطأ في إنشاء الورقة: " + str(e2))
                df_ops = pd.DataFrame()

        if not df_ops.empty:
            # ── تأكد من وجود الأعمدة ──
            required_cols = ["رقم المؤشر", "المؤشر", "النوع", "الاتجاه",
                             "المستهدف 2026", "المتحقق", "النسبة", "ملاحظات"]
            for c in required_cols:
                if c not in df_ops.columns:
                    df_ops[c] = ""

            # إضافة قيم افتراضية للأعمدة الجديدة إن كانت فارغة
            _default_noa = {
                "عدد القياسات/ المعايرات المنفذة":                  ("عدد",  "تصاعدي"),
                "نسبة المعايرات المنجزة في الوقت المحدد":            ("نسبة", "تصاعدي"),
                "الفترة الزمنية المستغرقة لمعايرة/قياس جهاز":       ("عدد",  "تنازلي"),
                "عدد الأجهزة المدروسة":                              ("عدد",  "تصاعدي"),
                "نسبة جهات تقويم المطابقة المسندة للمركز":          ("نسبة", "تصاعدي"),
                "عدد الجهات المرتبطة بالوقت الوطني":                ("عدد",  "تصاعدي"),
                "عدد مرات الدخول على نظام الوقت":                   ("عدد",  "تصاعدي"),
                "نسبة انجاز خطة انتاج المواد المرجعية المستهدفة":   ("نسبة", "تصاعدي"),
                "عدد المستفيدين من برامج اختبار الكفاءة الفنية":    ("عدد",  "تصاعدي"),
                "عدد برامج الكفاءة الفنية المقدمة":                 ("عدد",  "تصاعدي"),
                "عدد تقارير الكفاءة الفنية الصادرة":                ("عدد",  "تصاعدي"),
            }
            for idx_r, row_r in df_ops.iterrows():
                kpi_r = str(row_r["المؤشر"]).strip()
                if kpi_r in _default_noa:
                    if not str(row_r.get("النوع","")).strip():
                        df_ops.at[idx_r, "النوع"]    = _default_noa[kpi_r][0]
                    if not str(row_r.get("الاتجاه","")).strip():
                        df_ops.at[idx_r, "الاتجاه"]  = _default_noa[kpi_r][1]

            df_ops["المستهدف 2026"] = df_ops["المستهدف 2026"].apply(safe_float)
            df_ops["المتحقق"]       = df_ops["المتحقق"].apply(safe_float)

            # ── حساب النسبة بناءً على الاتجاه ──
            def calc_ops_pct(row):
                t = safe_float(row["المستهدف 2026"])
                a = safe_float(row["المتحقق"])
                if t == 0:
                    return 0.0
                pct = round((a / t) * 100, 1)
                return pct

            df_ops["النسبة"] = df_ops.apply(calc_ops_pct, axis=1)

            # ── بطاقات الملخص ──
            def _is_good(row):
                d = str(row.get("الاتجاه","تصاعدي")).strip()
                p = safe_float(row["النسبة"])
                return (p >= 100) if d == "تصاعدي" else (p <= 100)

            good_n  = sum(1 for _, r in df_ops.iterrows() if _is_good(r))
            avg_pct = round(df_ops["النسبة"].mean(), 1)
            achieved = len(df_ops[df_ops["النسبة"] >= 100])
            on_track = len(df_ops[(df_ops["النسبة"] >= 50) & (df_ops["النسبة"] < 100)])
            behind   = len(df_ops[df_ops["النسبة"] < 50])
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📊 متوسط الإنجاز",  str(avg_pct) + "%")
            c2.metric("✅ مكتمل (≥100%)",  achieved)
            c3.metric("🟡 جارٍ (50-99%)",  on_track)
            c4.metric("🔴 متأخر (<50%)",   behind)
            st.markdown("---")

            # ── فلترة ──
            filter_opt = st.radio(
                "عرض:",
                ["الكل", "✅ مكتمل", "🟡 جارٍ", "🔴 متأخر"],
                horizontal=True, key="ops_filter",
            )
            if filter_opt == "✅ مكتمل":
                df_show = df_ops[df_ops["النسبة"] >= 100].copy()
            elif filter_opt == "🟡 جارٍ":
                df_show = df_ops[(df_ops["النسبة"] >= 50) & (df_ops["النسبة"] < 100)].copy()
            elif filter_opt == "🔴 متأخر":
                df_show = df_ops[df_ops["النسبة"] < 50].copy()
            else:
                df_show = df_ops.copy()

            # ── تنسيق الأرقام أولاً (قبل style) ──
            def fmt_num(v):
                try:
                    f = float(v)
                    return int(f) if f == int(f) else round(f, 2)
                except:
                    return v

            df_show = df_show.copy()
            df_show["المستهدف 2026"] = df_show["المستهدف 2026"].apply(fmt_num).astype(str)
            df_show["المتحقق"]       = df_show["المتحقق"].apply(fmt_num).astype(str)

            # ── تلوين النسبة بناءً على الاتجاه ──
            def color_pct_row(row):
                styles = [""] * len(row)
                col_idx = list(row.index).index("النسبة") if "النسبة" in row.index else -1
                if col_idx < 0:
                    return styles
                v   = safe_float(row["النسبة"])
                d   = str(row.get("الاتجاه","تصاعدي")).strip()
                good = (v >= 100) if d == "تصاعدي" else (v <= 100)
                mid  = (50 <= v < 100) if d == "تصاعدي" else (100 < v <= 150)
                if good:
                    s = "color: #27ae60; font-weight: bold"
                elif mid:
                    s = "color: #d35400; font-weight: bold"
                else:
                    s = "color: #c0392b; font-weight: bold; background-color: #fde8e8"
                styles[col_idx] = s
                return styles

            styled = df_show.style.apply(color_pct_row, axis=1)

            st.dataframe(
                styled,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "رقم المؤشر":    st.column_config.NumberColumn("#", width="small", format="%d"),
                    "المؤشر":        st.column_config.TextColumn("المؤشر", width="large"),
                    "النوع":         st.column_config.TextColumn("النوع", width="small"),
                    "الاتجاه":       st.column_config.TextColumn("الاتجاه", width="small"),
                    "المستهدف 2026": st.column_config.TextColumn("المستهدف 2026"),
                    "المتحقق":       st.column_config.TextColumn("المتحقق"),
                    "النسبة":        st.column_config.NumberColumn("النسبة %", format="%.1f%%"),
                    "ملاحظات":       st.column_config.TextColumn("ملاحظات", width="medium"),
                },
            )

            # ── مخطط شريطي ──
            st.markdown("#### 📊 مقارنة بصرية")
            chart_df = df_show.copy()
            names  = [str(int(r["رقم المؤشر"])) + ". " + str(r["المؤشر"])
                      for _, r in chart_df.iterrows()]
            pcts   = chart_df["النسبة"].tolist()
            clrs   = []
            for p in pcts:
                if p >= 100:   clrs.append("#27ae60")
                elif p >= 50:  clrs.append("#f39c12")
                else:          clrs.append("#e74c3c")

            import plotly.graph_objects as go
            fig_ops = go.Figure(go.Bar(
                x=pcts, y=names, orientation="h",
                marker_color=clrs,
                text=[str(p) + "%" for p in pcts],
                textposition="outside",
            ))
            fig_ops.add_vline(x=100, line_dash="dash", line_color="#27ae60",
                              annotation_text="المستهدف 100%")
            # عناوين كاملة في المخطط
            max_name_len = max((len(n) for n in names), default=20)
            left_margin  = min(max_name_len * 7, 380)

            fig_ops.update_layout(
                xaxis=dict(range=[0, max(max(pcts, default=0)*1.2, 120)],
                           title="نسبة الإنجاز %", showgrid=True, gridcolor="#f0f0f0"),
                yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(t=20, b=40, l=left_margin, r=90),
                height=max(300, len(chart_df) * 52),
                showlegend=False,
            )
            st.plotly_chart(fig_ops, use_container_width=True, key="ops_bar_chart")

            # ── التتبع التاريخي ──
            st.markdown("---")
            st.markdown("#### 📈 التتبع التاريخي للمؤشر")
            df_ops_hist = load_ops_history(SHEET_ID + "_ops")
            if df_ops_hist.empty:
                st.info("لا يوجد سجل تاريخي بعد — سيُحفظ تلقائياً عند كل تحديث.")
            else:
                recorded_ops = df_ops_hist["KPI_Name"].astype(str).str.strip().unique().tolist()
                sel_hist_ops = st.selectbox(
                    "اختر المؤشر لعرض اتجاهه:",
                    ["— اختر —"] + recorded_ops,
                    key="ops_hist_select",
                )
                if sel_hist_ops and sel_hist_ops != "— اختر —":
                    row_dir = df_ops[df_ops["المؤشر"].astype(str).str.strip() == sel_hist_ops.strip()]
                    drx_ops = str(row_dir["الاتجاه"].values[0]).strip() if not row_dir.empty else "تصاعدي"
                    plot_ops_trend(df_ops_hist, sel_hist_ops, drx_ops, ctx="_adm_ops")
                    with st.expander("➕ إضافة قيمة تاريخية يدوية"):
                        with st.form("ops_manual_entry"):
                            mc1, mc2, mc3 = st.columns(3)
                            with mc1:
                                m_date = st.date_input("التاريخ", value=date.today(), key="ops_md")
                            with mc2:
                                m_act = st.number_input("القيمة الفعلية", value=0.0, key="ops_ma")
                            with mc3:
                                r_dir2 = df_ops[df_ops["المؤشر"].astype(str).str.strip()==sel_hist_ops.strip()]
                                m_tgt  = safe_float(r_dir2["المستهدف 2026"].values[0]) if not r_dir2.empty else 0.0
                                m_tgt2 = st.number_input("المستهدف", value=m_tgt, key="ops_mt")
                            m_note = st.text_input("ملاحظة", key="ops_mn")
                            if st.form_submit_button("💾 حفظ"):
                                save_ops_snapshot(sel_hist_ops, m_act, m_tgt2, user_name,
                                                  m_note or "إدخال يدوي")
                                st.success("✅ تم الحفظ!")
                                time.sleep(1)
                                st.rerun()

            # ── تحديث البيانات — متاح لـ f.qahtany فقط أو Admin ──
            st.markdown("---")
            _ops_user = st.session_state["user_info"].get("username", "").strip()
            _ops_role = str(st.session_state["user_info"].get("role", "")).strip().title()
            _can_edit_ops = (_ops_user == "f.qahtany" or _ops_role == "Admin")

            if _can_edit_ops:
                st.markdown("#### ✏️ تحديث قيمة المتحقق")
                col_sel, col_val, col_note = st.columns([3, 2, 3])
                with col_sel:
                    sel_ops = st.selectbox(
                        "اختر المؤشر:",
                        df_ops["المؤشر"].tolist(),
                        key="ops_select",
                    )
                if sel_ops:
                    ops_row = df_ops[df_ops["المؤشر"] == sel_ops].iloc[0]
                    with col_val:
                        new_actual = st.number_input(
                            "القيمة المتحققة",
                            value=float(ops_row["المتحقق"]),
                            key="ops_actual",
                        )
                    with col_note:
                        ops_note = st.text_input("ملاحظة", value=str(ops_row["ملاحظات"]), key="ops_note")
                    if st.button("💾 حفظ التحديث", use_container_width=True, key="ops_save"):
                        with st.spinner("جاري الحفظ..."):
                            try:
                                ws_ops2 = sh.worksheet("Operational_KPIs")
                                df_ops2 = pd.DataFrame(ws_ops2.get_all_records())
                                mask_ops = df_ops2["المؤشر"] == sel_ops
                                if mask_ops.any():
                                    df_ops2.loc[mask_ops, "المتحقق"]  = new_actual
                                    df_ops2.loc[mask_ops, "ملاحظات"]  = ops_note
                                    t_val = safe_float(df_ops2.loc[mask_ops, "المستهدف 2026"].values[0])
                                    pct_new = round((new_actual / t_val) * 100, 1) if t_val else 0
                                    df_ops2.loc[mask_ops, "النسبة"] = pct_new
                                    cdf_ops = clean_df_for_gspread(df_ops2)
                                    ws_ops2.update(
                                        values=[cdf_ops.columns.tolist()] + cdf_ops.values.tolist(),
                                        range_name="A1",
                                    )
                                    st.success("✅ تم الحفظ! النسبة الجديدة: " + str(pct_new) + "%")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error("خطأ: " + str(e))
            else:
                st.info("👁️ عرض للاطلاع فقط — تحديث البيانات متاح لمسؤول العمليات.")

    elif view == "🏥 صحة المبادرات":
        show_health_dashboard(df_acts)

    elif view == "📈 التتبع التاريخي":
        if df_kpi is None:
            st.error("تعذّر تحميل المؤشرات.")
        else:
            df_history = load_kpi_history(SHEET_ID)
            sub1, sub2 = st.tabs(["🗺️ نظرة عامة على الاتجاهات", "🔍 تحليل مؤشر بعينه"])
            with sub1:
                show_history_overview(df_history, df_kpi)
            with sub2:
                st.markdown("### 🔍 تحليل مؤشر بعينه")
                sel_kpi = st.selectbox("اختر المؤشر:", df_kpi["KPI_Name"].tolist(), key="single_kpi")
                if sel_kpi:
                    ki   = df_kpi[df_kpi["KPI_Name"].astype(str).str.strip() == sel_kpi.strip()]
                    unit = ki["Unit"].values[0]      if not ki.empty and "Unit"      in ki.columns else ""
                    drx  = ki["Direction"].values[0] if not ki.empty and "Direction" in ki.columns else "تصاعدي"
                    tgt  = ki["Target"].values[0]    if not ki.empty else 0.0
                    kh   = df_history[
                        df_history["KPI_Name"].astype(str).str.strip() == sel_kpi.strip()
                    ].sort_values("Date")
                    if not kh.empty:
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("عدد السجلات", len(kh))
                        m2.metric("آخر قيمة",    str(round(float(kh["Actual"].iloc[-1]), 1)))
                        m3.metric("أعلى قيمة",   str(round(float(kh["Actual"].max()), 1)))
                        m4.metric("أدنى قيمة",   str(round(float(kh["Actual"].min()), 1)))
                    plot_kpi_trend(df_history, sel_kpi, drx, unit, ctx="_adm3")
                    st.markdown("---")
                    st.markdown("##### ➕ إضافة قيمة تاريخية يدوية")
                    with st.form("manual_entry"):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            md = st.date_input("التاريخ", value=date.today())
                        with c2:
                            ma = st.number_input("القيمة الفعلية", value=0.0)
                        with c3:
                            mt = st.number_input("المستهدف", value=float(tgt))
                        mn = st.text_input("ملاحظة (اختياري)")
                        if st.form_submit_button("💾 حفظ القيمة"):
                            try:
                                ws_h     = _get_or_create_history_ws(get_sheet_connection())
                                note_val = mn if mn else "إدخال يدوي"
                                ws_h.append_row([sel_kpi, str(md), ma, mt, user_name, note_val])
                                load_kpi_history.clear()
                                st.success("✅ تم الحفظ!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error("خطأ: " + str(e))

    elif view == "📷 تسجيل لقطة شاملة":
        st.markdown("### 📷 تسجيل لقطة شاملة لجميع المؤشرات")
        st.markdown(
            "<div class='snapshot-info'>📌 <b>متى تستخدم هذا؟</b><br>"
            "• في نهاية كل ربع أو شهر لحفظ حالة جميع المؤشرات دفعةً واحدة.<br>"
            "• المؤشرات تُحفظ تلقائياً أيضاً عند تحديث كل مالك لمؤشره.</div>",
            unsafe_allow_html=True,
        )
        if df_kpi is not None:
            prev = df_kpi[["KPI_Name", "Actual", "Target"]].copy()
            prev.columns = ["المؤشر", "القيمة الفعلية", "المستهدف"]
            st.dataframe(
                prev, hide_index=True, use_container_width=True,
                column_config={
                    "القيمة الفعلية": st.column_config.NumberColumn(format="%.1f"),
                    "المستهدف":        st.column_config.NumberColumn(format="%.1f"),
                },
            )
            c_btn, _ = st.columns([1, 3])
            with c_btn:
                if st.button("📷 تسجيل لقطة الآن", type="primary", use_container_width=True):
                    n_kpi = len(df_kpi)
                    with st.spinner("جاري تسجيل " + str(n_kpi) + " مؤشر..."):
                        n = save_all_kpis_snapshot(df_kpi, user_name)
                    if n > 0:
                        st.success("✅ تم تسجيل " + str(n) + " مؤشر بتاريخ " + date.today().isoformat())
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.info("جميع مؤشرات اليوم مُسجَّلة بالفعل.")
            df_history = load_kpi_history(SHEET_ID)
            if not df_history.empty:
                last_d = df_history["Date"].max()
                n_last = len(df_history[df_history["Date"] == last_d])
                ld_str = last_d.strftime("%Y-%m-%d")
                st.caption("آخر لقطة: **" + ld_str + "** — " + str(n_last) +
                           " مؤشر | إجمالي السجلات: " + str(len(df_history)))

    elif view == "📄 تصدير PDF":
        if df_kpi is None:
            st.error("تعذّر تحميل بيانات المؤشرات.")
        else:
            df_kpi["Category"] = df_kpi["KPI_Name"].apply(get_kpi_category)

            def _make_group_fig(group_df, title):
                if group_df.empty:
                    return None
                def gc(row):
                    t = row["Target"]
                    a = row["Actual"]
                    d = str(row.get("Direction", "تصاعدي")).strip()
                    if d == "تنازلي":
                        return "#2ca02c" if a <= t else "#d62728"
                    return "#1f77b4" if a > t else ("#2ca02c" if a == t else "#d62728")
                group_df = group_df.copy()
                group_df["Color"] = group_df.apply(gc, axis=1)
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=group_df["KPI_Name"], y=group_df["Actual"],
                    name="الفعلي", marker_color=group_df["Color"],
                    text=group_df["Actual"], textposition="auto",
                ))
                fig.add_trace(go.Scatter(
                    x=group_df["KPI_Name"], y=group_df["Target"],
                    mode="markers", name="المستهدف",
                    marker=dict(symbol="line-ew", size=30, color="black", line=dict(width=2)),
                ))
                fig.update_layout(
                    title=dict(text=title, x=0.5, xanchor="center"),
                    barmode="overlay", height=320,
                    plot_bgcolor="white", paper_bgcolor="white",
                    margin=dict(t=50, b=40, l=30, r=20),
                    legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
                )
                return fig

            kpi_figs = {}
            fig_qi = _make_group_fig(df_kpi[df_kpi["Category"] == "QI4SD"],              "مجموعة QI4SD")
            fig_rd = _make_group_fig(df_kpi[df_kpi["Category"] == "البحث والتطوير"],     "مجموعة البحث والتطوير")
            fig_op = _make_group_fig(df_kpi[df_kpi["Category"] == "الكفاءة التشغيلية"], "مجموعة الكفاءة التشغيلية")
            if fig_qi:
                kpi_figs["مجموعة QI4SD"]             = fig_qi
            if fig_rd:
                kpi_figs["مجموعة البحث والتطوير"]    = fig_rd
            if fig_op:
                kpi_figs["مجموعة الكفاءة التشغيلية"] = fig_op

            try:
                df_hist_export = load_kpi_history(SHEET_ID)
                if not df_hist_export.empty:
                    for kpi_name_e in df_hist_export["KPI_Name"].unique()[:4]:
                        kh_e = df_hist_export[
                            df_hist_export["KPI_Name"].astype(str).str.strip() == kpi_name_e.strip()
                        ].sort_values("Date")
                        if len(kh_e) >= 2:
                            trend_fig = go.Figure()
                            trend_fig.add_trace(go.Scatter(
                                x=kh_e["Date"], y=kh_e["Actual"],
                                mode="lines+markers", name=kpi_name_e[:30],
                                line=dict(color="#0068c9", width=2),
                            ))
                            trend_fig.add_trace(go.Scatter(
                                x=kh_e["Date"], y=kh_e["Target"],
                                mode="lines", name="المستهدف",
                                line=dict(color="#e67e22", width=1.5, dash="dot"),
                            ))
                            trend_fig.update_layout(
                                title=dict(text="اتجاه: " + kpi_name_e[:40], x=0.5, xanchor="center"),
                                height=260, plot_bgcolor="white", paper_bgcolor="white",
                                margin=dict(t=40, b=30, l=30, r=20),
                                legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
                                xaxis=dict(tickformat="%b %Y"),
                            )
                            kpi_figs["اتجاه: " + kpi_name_e[:30]] = trend_fig
            except Exception:
                pass

            try:
                from pdf_export import show_export_section
                show_export_section(df_kpi, df_acts, kpi_figs, user_name)
            except ImportError:
                st.warning("ملف pdf_export.py غير موجود. ارفعه مع dashboard.py على GitHub.")

    elif view == "💬 المحادثات":
        st.markdown("### 💬 محادثات المبادرات والمؤشرات")
        chat_type = st.radio(
            "نوع المحادثة:",
            ["📋 نشاط محدد", "📊 مؤشر محدد"],
            horizontal=True, key="admin_chat_type",
        )
        if chat_type == "📋 نشاط محدد":
            col1, col2 = st.columns(2)
            with col1:
                sel_init_chat = st.selectbox(
                    "المبادرة:", df_acts["Mabadara"].unique(), key="chat_init"
                )
            acts_in_chat = df_acts[df_acts["Mabadara"] == sel_init_chat]
            with col2:
                sel_act_chat = st.selectbox(
                    "النشاط:", acts_in_chat["Activity"].unique(), key="chat_act"
                )
            if sel_init_chat and sel_act_chat:
                show_activity_chat(ws_acts, df_acts, sel_init_chat, sel_act_chat,
                                   "Admin", user_name)
        else:
            if df_kpi is not None:
                sel_kpi_chat = st.selectbox(
                    "المؤشر:", df_kpi["KPI_Name"].unique(), key="chat_kpi"
                )
                if sel_kpi_chat:
                    show_kpi_chat(ws_kpi, df_kpi, sel_kpi_chat, "Admin", user_name)

# ---------------------------------------------------------
# 12. واجهة المالك
# ---------------------------------------------------------


def owner_view(sh, user_name, my_initiatives_str):
    my_list = (
        [x.strip() for x in str(my_initiatives_str).split(",") if x.strip()]
        if my_initiatives_str else []
    )
    try:
        ws_acts  = sh.worksheet("Activities")
        all_data = pd.DataFrame(ws_acts.get_all_records())
        all_data["Mabadara"] = all_data["Mabadara"].astype(str).str.strip()
        all_data["Activity"] = all_data["Activity"].astype(str).str.strip()
        for c in ["Admin_Comment", "Owner_Comment"]:
            if c not in all_data.columns:
                all_data[c] = ""
        my_data = all_data[all_data["Mabadara"].isin(my_list)].copy()

        ws_kpi  = sh.worksheet("KPIs")
        df_kpi  = pd.DataFrame(ws_kpi.get_all_records())
        for c in ["Admin_Comment", "Owner_Comment", "Owner"]:
            if c not in df_kpi.columns:
                df_kpi[c] = ""
        df_kpi["Target"] = df_kpi["Target"].apply(safe_float)
        df_kpi["Actual"] = df_kpi["Actual"].apply(safe_float)
    except Exception as e:
        st.error("خطأ في تحميل البيانات: " + str(e))
        return

    show_owner_alerts(all_data, my_list)

    view = st.selectbox(
        "القسم:",
        (
            ["📅 مخطط الخطة", "📋 تحديث الأنشطة", "✏️ تحديث مؤشراتي", "⚙️ المؤشرات التشغيلية",
             "🏥 صحة مبادراتي", "📈 اتجاه مؤشراتي", "📊 كافة المؤشرات", "💬 محادثاتي"]
            if st.session_state["user_info"].get("username","").strip() == "f.qahtany"
            else ["📅 مخطط الخطة", "📋 تحديث الأنشطة", "✏️ تحديث مؤشراتي",
                  "🏥 صحة مبادراتي", "📈 اتجاه مؤشراتي", "📊 كافة المؤشرات", "💬 محادثاتي"]
        ),
        key="owner_view_select",
    )
    st.markdown("---")


    if view == "📅 مخطط الخطة":
        st.markdown("### 📅 مخطط الخطة الزمنية")
        if not my_list:
            st.warning("لا توجد مبادرات مسندة إليك.")
        else:
            # ── فلترة ──
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                sel_init_g = st.selectbox(
                    "المبادرة:",
                    ["الكل"] + list(my_data["Mabadara"].unique()),
                    key="gantt_init",
                )
            with c_f2:
                gantt_status = st.radio(
                    "الحالة:",
                    ["الكل", "✅ مكتملة", "🟡 جارية", "🔴 متأخرة"],
                    horizontal=True, key="gantt_status",
                )

            df_g = my_data.copy() if sel_init_g == "الكل" else                    my_data[my_data["Mabadara"] == sel_init_g].copy()

            # تحضير التواريخ والإنجاز
            df_g["_start"] = pd.to_datetime(df_g["Start_Date"], errors="coerce")
            df_g["_end"]   = pd.to_datetime(df_g["End_Date"],   errors="coerce")
            df_g["_prog"]  = df_g["Progress"].apply(safe_int)
            df_g = df_g.dropna(subset=["_start", "_end"])

            today_g = pd.Timestamp(date.today())

            def _gantt_status(row):
                late = row["_end"] < today_g and row["_prog"] < 100
                if row["_prog"] >= 100: return "done"
                if late:                return "late"
                return "progress"

            df_g["_status"] = df_g.apply(_gantt_status, axis=1)

            if gantt_status == "✅ مكتملة":
                df_g = df_g[df_g["_status"] == "done"]
            elif gantt_status == "🟡 جارية":
                df_g = df_g[df_g["_status"] == "progress"]
            elif gantt_status == "🔴 متأخرة":
                df_g = df_g[df_g["_status"] == "late"]

            if df_g.empty:
                st.info("لا توجد أنشطة في هذه الفئة.")
            else:
                df_g = df_g.sort_values("_start")

                # ── ألوان الحالة ──
                def bar_color_g(row):
                    if row["_prog"] >= 100: return "#3B6D11"
                    if row["_status"] == "late": return "#A32D2D"
                    if row["_prog"] >= 50:  return "#185FA5"
                    return "#BA7517"

                # ══ Gantt بـ go.Bar الصحيح — تواريخ كـ timestamps ══
                fig_g = go.Figure()
                n_acts = len(df_g)
                act_labels = list(df_g["Activity"].astype(str))

                for i, (_, row) in enumerate(df_g.iterrows()):
                    col_g   = bar_color_g(row)
                    pct_g   = int(row["_prog"])
                    s_dt    = row["_start"]
                    e_dt    = row["_end"]
                    dur_ms  = int((e_dt - s_dt).total_seconds() * 1000)
                    prog_ms = int(dur_ms * pct_g / 100)
                    act_lbl = str(row["Activity"])
                    stat_lbl = ("متأخر" if row["_status"]=="late"
                                else ("مكتمل" if pct_g>=100 else "جارٍ"))
                    base_ms = int(s_dt.timestamp() * 1000)

                    # خلفية كاملة
                    fig_g.add_trace(go.Bar(
                        x=[dur_ms], y=[act_lbl],
                        base=[base_ms],
                        orientation="h",
                        marker_color="rgba(180,178,169,0.2)",
                        marker_line_width=0,
                        showlegend=False,
                        hoverinfo="skip",
                        width=0.5,
                    ))
                    # شريط الإنجاز
                    fig_g.add_trace(go.Bar(
                        x=[max(prog_ms, int(dur_ms*0.01))],
                        y=[act_lbl],
                        base=[base_ms],
                        orientation="h",
                        marker_color=col_g,
                        marker_line_width=0,
                        showlegend=False,
                        width=0.5,
                        text=str(pct_g) + "%" if pct_g > 5 else "",
                        textposition="inside",
                        textfont=dict(color="white", size=10),
                        customdata=[[
                            str(row.get("Mabadara","")),
                            act_lbl,
                            s_dt.strftime("%Y-%m-%d"),
                            e_dt.strftime("%Y-%m-%d"),
                            pct_g, stat_lbl,
                        ]],
                        hovertemplate=(
                            "<b>%{customdata[1]}</b><br>"
                            "المبادرة: %{customdata[0]}<br>"
                            "البداية: %{customdata[2]}<br>"
                            "النهاية: %{customdata[3]}<br>"
                            "الإنجاز: <b>%{customdata[4]}%%</b><br>"
                            "الحالة: <b>%{customdata[5]}</b>"
                            "<extra></extra>"
                        ),
                    ))

                # خط اليوم
                fig_g.add_vline(
                    x=int(today_g.timestamp() * 1000),
                    line_width=1.5, line_dash="dash", line_color="#555",
                    annotation_text="اليوم",
                    annotation_position="top",
                    annotation_font_size=11,
                )

                min_ts = int((df_g["_start"].min() - pd.Timedelta(days=15)).timestamp() * 1000)
                max_ts = int((df_g["_end"].max()   + pd.Timedelta(days=15)).timestamp() * 1000)
                chart_height = max(350, n_acts * 50 + 100)

                # هامش ديناميكي بناءً على أطول اسم نشاط
                max_act_len = max((len(str(a)) for a in df_g["Activity"]), default=10)
                left_margin = min(max_act_len * 7, 320)

                fig_g.update_layout(
                    barmode="overlay",
                    height=chart_height,
                    xaxis=dict(
                        type="date",
                        range=[min_ts, max_ts],
                        tickformat="%b %Y",
                        showgrid=True,
                        gridcolor="#eeeeee",
                        zeroline=False,
                        title="",
                        tickangle=-30,
                        side="top",
                    ),
                    yaxis=dict(
                        autorange="reversed",
                        showgrid=True,
                        gridcolor="#f5f5f5",
                        title="",
                        tickfont=dict(size=12, family="Tajawal"),
                        tickmode="array",
                        tickvals=list(range(n_acts)),
                        ticktext=[
                            (str(a)[:35] + "…") if len(str(a)) > 35 else str(a)
                            for a in df_g["Activity"]
                        ],
                        side="right",
                    ),
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    margin=dict(t=60, b=40, l=20, r=left_margin),
                    hoverlabel=dict(bgcolor="white", font_size=12, font_family="Tajawal"),
                    font=dict(family="Tajawal"),
                    showlegend=False,
                )
                st.plotly_chart(fig_g, use_container_width=True, key="owner_gantt")

                # ── مفتاح الألوان ──
                legend_cols = st.columns(4)
                legend_cols[0].markdown(
                    "<span style='display:inline-block;width:14px;height:14px;"
                    "background:#3B6D11;border-radius:3px;margin-left:6px'></span>"
                    "<span style='font-size:12px;color:#1e8449'>مكتمل ≥100%</span>",
                    unsafe_allow_html=True,
                )
                legend_cols[1].markdown(
                    "<span style='display:inline-block;width:14px;height:14px;"
                    "background:#185FA5;border-radius:3px;margin-left:6px'></span>"
                    "<span style='font-size:12px;color:#185FA5'>جارٍ ≥50%</span>",
                    unsafe_allow_html=True,
                )
                legend_cols[2].markdown(
                    "<span style='display:inline-block;width:14px;height:14px;"
                    "background:#BA7517;border-radius:3px;margin-left:6px'></span>"
                    "<span style='font-size:12px;color:#854F0B'>منخفض <50%</span>",
                    unsafe_allow_html=True,
                )
                legend_cols[3].markdown(
                    "<span style='display:inline-block;width:14px;height:14px;"
                    "background:#A32D2D;border-radius:3px;margin-left:6px'></span>"
                    "<span style='font-size:12px;color:#A32D2D'>متأخر</span>",
                    unsafe_allow_html=True,
                )

                # ── ملخص سريع ──
                st.markdown("---")
                n_done  = len(df_g[df_g["_status"] == "done"])
                n_prog  = len(df_g[df_g["_status"] == "progress"])
                n_late  = len(df_g[df_g["_status"] == "late"])
                avg_p   = round(df_g["_prog"].mean(), 1)
                ms1,ms2,ms3,ms4 = st.columns(4)
                ms1.metric("📊 متوسط الإنجاز", str(avg_p) + "%")
                ms2.metric("✅ مكتملة",         n_done)
                ms3.metric("🟡 جارية",          n_prog)
                ms4.metric("🔴 متأخرة",         n_late)

    elif view == "📋 تحديث الأنشطة":
        st.markdown("### 📌 تحديث أنشطة المبادرات")
        if not my_list:
            st.warning("لا توجد مبادرات مسندة إليك.")
        else:
            sel_init = st.selectbox("اختر المبادرة", my_data["Mabadara"].unique())
            with st.expander("➕ إضافة نشاط جديد"):
                with st.form("add_act"):
                    nn = st.text_input("اسم النشاط")
                    c1, c2 = st.columns(2)
                    with c1:
                        ns = st.date_input("البداية", key="ns")
                    with c2:
                        ne = st.date_input("النهاية", key="ne")
                    if st.form_submit_button("إضافة"):
                        if nn.strip():
                            try:
                                ws_acts.append_row([sel_init, nn, str(ns), str(ne), 0, "", "", ""])
                                st.success("تمت الإضافة!")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error("خطأ: " + str(e))
                        else:
                            st.error("أدخل اسم النشاط")

            acts = my_data[my_data["Mabadara"] == sel_init]
            if not acts.empty:
                sel_act = st.selectbox("النشاط", acts["Activity"].unique(),
                                       label_visibility="collapsed")
                if sel_act:
                    row = acts[acts["Activity"] == sel_act].iloc[0]

                    with st.expander("⚙️ إعدادات النشاط (تعديل / حذف)"):
                        st.info("هذه الإجراءات تؤثر على هيكل النشاط.")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("##### ✏️ تعديل المسمى")
                            nv = st.text_input("الاسم الجديد", value=sel_act, key="ren")
                            if st.button("تحديث الاسم"):
                                if nv.strip() != sel_act:
                                    try:
                                        cell = ws_acts.find(sel_act)
                                        if cell:
                                            ws_acts.update_cell(cell.row, cell.col, nv)
                                            st.success("تم!")
                                            time.sleep(1)
                                            st.rerun()
                                    except Exception as e:
                                        st.error(str(e))
                                else:
                                    st.warning("الاسم مطابق.")
                        with c2:
                            st.markdown("##### 🗑️ حذف النشاط")
                            st.warning("سيتم حذف النشاط بالكامل.")
                            if st.button("تأكيد الحذف", type="primary"):
                                try:
                                    cell = ws_acts.find(sel_act)
                                    if cell:
                                        ws_acts.delete_rows(cell.row)
                                        st.success("تم الحذف.")
                                        time.sleep(1)
                                        st.rerun()
                                except Exception as e:
                                    st.error(str(e))

                    ac_val = str(row.get("Admin_Comment", "")).strip()
                    if ac_val:
                        st.markdown(
                            "<div class='admin-alert-box'>📢 <strong>ملاحظة من المدير:</strong>"
                            "<div class='history-box'>" + ac_val + "</div></div>",
                            unsafe_allow_html=True,
                        )

                    with st.form("upd_form"):
                        st.markdown("#### 📝 بيانات النشاط")
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            ns2 = st.date_input("تاريخ البداية",
                                                value=parse_date(row["Start_Date"]))
                        with c2:
                            ne2 = st.date_input("تاريخ النهاية",
                                                value=parse_date(row["End_Date"]))
                        with c3:
                            np2 = st.number_input("نسبة الإنجاز %", min_value=0, max_value=100,
                                                  value=safe_int(row["Progress"]), step=1)
                        el = st.text_input("رابط الدليل (URL)", value=str(row["Evidence_Link"]))
                        st.markdown("📜 **سجل الملاحظات السابق:**")
                        pn = str(row["Owner_Comment"])
                        if pn:
                            st.markdown("<div class='history-box'>" + pn + "</div>",
                                        unsafe_allow_html=True)
                        else:
                            st.caption("لا توجد ملاحظات سابقة.")
                        nn2 = st.text_area("✍️ إضافة ملاحظة جديدة", height=100)
                        if st.form_submit_button("💾 حفظ التحديث"):
                            try:
                                sh2  = get_sheet_connection()
                                ws2  = sh2.worksheet("Activities")
                                df2  = pd.DataFrame(ws2.get_all_records())
                                df2["Mabadara"] = df2["Mabadara"].astype(str).str.strip()
                                df2["Activity"] = df2["Activity"].astype(str).str.strip()
                                mask2 = (
                                    (df2["Mabadara"] == sel_init) &
                                    (df2["Activity"] == sel_act)
                                )
                                if mask2.any():
                                    fc2 = append_timestamped_comment(pn, nn2)
                                    df2.loc[mask2, "Progress"]      = int(np2)
                                    df2.loc[mask2, "Start_Date"]    = str(ns2)
                                    df2.loc[mask2, "End_Date"]      = str(ne2)
                                    df2.loc[mask2, "Evidence_Link"] = str(el)
                                    df2.loc[mask2, "Owner_Comment"] = fc2
                                    cdf2 = clean_df_for_gspread(df2)
                                    ws2.update(
                                        values=[cdf2.columns.tolist()] + cdf2.values.tolist(),
                                        range_name="A1",
                                    )
                                    st.success("✅ تم الحفظ!")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error("خطأ: " + str(e))

    elif view == "✏️ تحديث مؤشراتي":
        st.markdown("### 📈 تحديث مؤشرات الأداء المسندة لي")
        cu = st.session_state["user_info"].get("username", "").strip()
        my_kpis = df_kpi[
            (df_kpi["Owner"].astype(str).str.strip() == cu) |
            (df_kpi["Owner"].astype(str).str.strip() == user_name.strip())
        ]
        if my_kpis.empty:
            st.info("لا توجد مؤشرات مرتبطة بحسابك.")
        else:
            sk2 = st.selectbox("اختر المؤشر", my_kpis["KPI_Name"].unique())
            if sk2:
                kr = my_kpis[my_kpis["KPI_Name"] == sk2].iloc[0]
                m1, m2, m3 = st.columns(3)
                m1.metric("المستهدف",       kr["Target"])
                m2.metric("المتحقق الحالي", kr["Actual"])
                m3.metric("الوحدة",         kr.get("Unit", "-"))
                ac_kr = str(kr.get("Admin_Comment", "")).strip()
                if ac_kr:
                    st.markdown(
                        "<div class='admin-alert-box'>📢 <strong>ملاحظات المدير:</strong>"
                        "<div class='history-box'>" + ac_kr + "</div></div>",
                        unsafe_allow_html=True,
                    )
                with st.form("upd_kpi"):
                    na2 = st.number_input("القيمة المتحققة", value=safe_float(kr["Actual"]))
                    st.write("💬 **سجل ملاحظاتك السابق:**")
                    pn2 = str(kr.get("Owner_Comment", ""))
                    if pn2:
                        st.markdown("<div class='history-box'>" + pn2 + "</div>",
                                    unsafe_allow_html=True)
                    nn3 = st.text_area("أضف ملاحظة جديدة:")
                    if st.form_submit_button("💾 حفظ تحديث المؤشر"):
                        try:
                            sh3  = get_sheet_connection()
                            ws3  = sh3.worksheet("KPIs")
                            df3  = pd.DataFrame(ws3.get_all_records())
                            if "Owner_Comment" not in df3.columns:
                                df3["Owner_Comment"] = ""
                            mask3 = df3["KPI_Name"] == sk2
                            if mask3.any():
                                fc3 = append_timestamped_comment(pn2, nn3)
                                df3.loc[mask3, "Actual"]        = na2
                                df3.loc[mask3, "Owner_Comment"] = fc3
                                cdf3 = clean_df_for_gspread(df3)
                                ws3.update(
                                    values=[cdf3.columns.tolist()] + cdf3.values.tolist(),
                                    range_name="A1",
                                )
                                tgt3  = safe_float(df3.loc[mask3, "Target"].values[0])
                                note3 = nn3[:80] if nn3 else "تحديث تلقائي"
                                save_kpi_snapshot(sk2, na2, tgt3, user_name, note3)
                                st.success("✅ تم تحديث المؤشر وحفظه في السجل التاريخي!")
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error("خطأ: " + str(e))

    elif view == "🏥 صحة مبادراتي":
        st.markdown("### 🏥 صحة مبادراتي")
        show_owner_health(all_data, my_list)

    elif view == "📈 اتجاه مؤشراتي":
        st.markdown("### 📈 اتجاه مؤشراتي")
        cu3   = st.session_state["user_info"].get("username", "").strip()
        my_k3 = df_kpi[
            (df_kpi["Owner"].astype(str).str.strip() == cu3) |
            (df_kpi["Owner"].astype(str).str.strip() == user_name.strip())
        ]
        if my_k3.empty:
            st.info("لا توجد مؤشرات مرتبطة بحسابك.")
        else:
            df_hist3 = load_kpi_history(SHEET_ID)
            for _, kr3 in my_k3.iterrows():
                kn3  = str(kr3["KPI_Name"]).strip()
                drx3 = str(kr3.get("Direction", "تصاعدي")).strip()
                unt3 = str(kr3.get("Unit", "")).strip()
                st.markdown("#### " + kn3)
                plot_kpi_trend(df_hist3, kn3, drx3, unt3, ctx="_own3")
                st.markdown("---")

    elif view == "📊 كافة المؤشرات":
        st.markdown("### 📊 لوحة المؤشرات العامة (للاطلاع)")
        display_kpi_layout(df_kpi, ctx="_own_tab5")


    elif view == "⚙️ المؤشرات التشغيلية":
        st.markdown("### ⚙️ تحديث المؤشرات التشغيلية")
        _ou = st.session_state["user_info"].get("username","").strip()
        if _ou != "f.qahtany":
            st.warning("هذا القسم مخصص لمسؤول العمليات.")
        else:
            try:
                ws_ops_o = sh.worksheet("Operational_KPIs")
                df_ops_o = pd.DataFrame(ws_ops_o.get_all_records())
            except Exception as e_ops:
                st.error("خطأ في تحميل البيانات: " + str(e_ops))
                df_ops_o = pd.DataFrame()

            if not df_ops_o.empty:
                df_ops_o["المستهدف 2026"] = df_ops_o["المستهدف 2026"].apply(safe_float)
                df_ops_o["المتحقق"]       = df_ops_o["المتحقق"].apply(safe_float)

                def calc_pct_o(row):
                    t = safe_float(row["المستهدف 2026"])
                    a = safe_float(row["المتحقق"])
                    return round((a / t) * 100, 1) if t else 0.0
                df_ops_o["النسبة"] = df_ops_o.apply(calc_pct_o, axis=1)

                def fmt_n(v):
                    try:
                        f = float(v)
                        return int(f) if f == int(f) else round(f, 2)
                    except:
                        return v
                df_ops_o = df_ops_o.copy()
                df_ops_o["المستهدف 2026"] = df_ops_o["المستهدف 2026"].apply(fmt_n).astype(str)
                df_ops_o["المتحقق"]       = df_ops_o["المتحقق"].apply(fmt_n).astype(str)

                # تلوين حسب الاتجاه
                def color_row_o(row):
                    styles = [""] * len(row)
                    ci = list(row.index).index("النسبة") if "النسبة" in row.index else -1
                    if ci < 0:
                        return styles
                    v = safe_float(row["النسبة"])
                    d = str(row.get("الاتجاه","تصاعدي")).strip()
                    good = (v >= 100) if d == "تصاعدي" else (v <= 100)
                    mid  = (50 <= v < 100) if d == "تصاعدي" else (100 < v <= 150)
                    if good:
                        styles[ci] = "color: #27ae60; font-weight: bold"
                    elif mid:
                        styles[ci] = "color: #d35400; font-weight: bold"
                    else:
                        styles[ci] = "color: #c0392b; font-weight: bold; background-color: #fde8e8"
                    return styles

                cols_o = [c for c in ["رقم المؤشر","المؤشر","النوع","الاتجاه",
                          "المستهدف 2026","المتحقق","النسبة","ملاحظات"]
                          if c in df_ops_o.columns]
                styled_o = df_ops_o[cols_o].style.apply(color_row_o, axis=1)

                # جدول للاطلاع
                st.dataframe(
                    styled_o,
                    hide_index=True, use_container_width=True,
                    column_config={
                        "رقم المؤشر":    st.column_config.NumberColumn("#", width="small", format="%d"),
                        "المؤشر":        st.column_config.TextColumn("المؤشر", width="large"),
                        "النوع":         st.column_config.TextColumn("النوع", width="small"),
                        "الاتجاه":       st.column_config.TextColumn("الاتجاه", width="small"),
                        "المستهدف 2026": st.column_config.TextColumn("المستهدف 2026"),
                        "المتحقق":       st.column_config.TextColumn("المتحقق"),
                        "النسبة":        st.column_config.NumberColumn("النسبة %", format="%.1f%%"),
                        "ملاحظات":       st.column_config.TextColumn("ملاحظات", width="medium"),
                    },
                )

                st.markdown("---")
                st.markdown("#### ✏️ تحديث قيمة المتحقق")
                sel_ops_o = st.selectbox(
                    "اختر المؤشر:",
                    df_ops_o["المؤشر"].tolist(),
                    key="ops_owner_select",
                )
                if sel_ops_o:
                    ops_row_o = df_ops_o[df_ops_o["المؤشر"] == sel_ops_o].iloc[0]
                    col_v, col_n = st.columns([2, 3])
                    with col_v:
                        new_act_o = st.number_input(
                            "القيمة المتحققة",
                            value=float(ops_row_o["المتحقق"]),
                            key="ops_owner_actual",
                        )
                    with col_n:
                        note_o = st.text_input(
                            "ملاحظة",
                            value=str(ops_row_o["ملاحظات"]),
                            key="ops_owner_note",
                        )
                    if st.button("💾 حفظ التحديث", use_container_width=True, key="ops_owner_save"):
                        with st.spinner("جاري الحفظ..."):
                            try:
                                ws_o2  = sh.worksheet("Operational_KPIs")
                                df_o2  = pd.DataFrame(ws_o2.get_all_records())
                                msk_o  = df_o2["المؤشر"] == sel_ops_o
                                if msk_o.any():
                                    df_o2.loc[msk_o, "المتحقق"]  = new_act_o
                                    df_o2.loc[msk_o, "ملاحظات"]  = note_o
                                    t_o = safe_float(df_o2.loc[msk_o, "المستهدف 2026"].values[0])
                                    pct_o = round((new_act_o / t_o) * 100, 1) if t_o else 0
                                    df_o2.loc[msk_o, "النسبة"] = pct_o
                                    cdf_o = clean_df_for_gspread(df_o2)
                                    ws_o2.update(
                                        values=[cdf_o.columns.tolist()] + cdf_o.values.tolist(),
                                        range_name="A1",
                                    )
                                    # حفظ في السجل التاريخي
                                    save_ops_snapshot(
                                        sel_ops_o, new_act_o,
                                        safe_float(df_o2.loc[msk_o, "المستهدف 2026"].values[0]),
                                        user_name,
                                        note_o[:80] if note_o else "تحديث",
                                    )
                                    st.success("✅ تم الحفظ! النسبة: " + str(pct_o) + "%")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error("خطأ: " + str(e))

            # ── عرض اتجاه المؤشر بعد التحديث ──
            st.markdown("---")
            st.markdown("#### 📈 الاتجاه التاريخي")
            df_ops_hist_o = load_ops_history(SHEET_ID + "_ops")
            if df_ops_hist_o.empty:
                st.info("لا يوجد سجل تاريخي بعد — سيُحفظ تلقائياً عند أول تحديث.")
            else:
                recorded_ops_o = df_ops_hist_o["KPI_Name"].astype(str).str.strip().unique().tolist()
                if recorded_ops_o:
                    sel_hist_o = st.selectbox(
                        "اختر المؤشر:",
                        ["— اختر —"] + recorded_ops_o,
                        key="ops_owner_hist_sel",
                    )
                    if sel_hist_o and sel_hist_o != "— اختر —":
                        rd = df_ops_o[df_ops_o["المؤشر"].astype(str).str.strip()==sel_hist_o.strip()]
                        drx_o2 = str(rd["الاتجاه"].values[0]).strip() if not rd.empty else "تصاعدي"
                        plot_ops_trend(df_ops_hist_o, sel_hist_o, drx_o2, ctx="_own_ops")

    elif view == "💬 محادثاتي":
        st.markdown("### 💬 محادثاتي مع المدير")
        if not my_list:
            st.warning("لا توجد مبادرات مسندة إليك.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                sel_init_oc = st.selectbox(
                    "المبادرة:", my_data["Mabadara"].unique(), key="oc_init"
                )
            acts_oc = my_data[my_data["Mabadara"] == sel_init_oc]
            with col2:
                sel_act_oc = st.selectbox(
                    "النشاط:", acts_oc["Activity"].unique(), key="oc_act"
                )
            if sel_init_oc and sel_act_oc:
                show_activity_chat(ws_acts, all_data, sel_init_oc, sel_act_oc,
                                   "Owner", user_name)

# ---------------------------------------------------------
# 13. واجهة المشاهد
# ---------------------------------------------------------


def viewer_view(sh, user_name):
    st.markdown("### 👋 مرحباً، " + user_name + " (نسخة للاطلاع)")
    try:
        ws_kpi = sh.worksheet("KPIs")
        df_kpi = pd.DataFrame(ws_kpi.get_all_records())
        if df_kpi.empty:
            st.info("لا توجد مؤشرات.")
            return
        df_kpi["Target"] = df_kpi["Target"].apply(safe_float)
        df_kpi["Actual"] = df_kpi["Actual"].apply(safe_float)
        display_kpi_layout(df_kpi, ctx="_viewer")
    except Exception as e:
        st.error("خطأ: " + str(e))

# ---------------------------------------------------------
# 14. التشغيل الرئيسي
# ---------------------------------------------------------
if not st.session_state["logged_in"]:
    login()
else:
    with st.container():
        ci, cs, cl, clo = st.columns([3, 4, 1, 1])
        with ci:
            user_name = st.session_state["user_info"]["name"]
            user_role = st.session_state["user_info"]["role"]
            st.markdown("### 👤 " + user_name)
            st.caption("الدور: " + user_role)
        with cl:
            st.write("")
            if st.button("تسجيل الخروج", use_container_width=True):
                st.session_state["logged_in"] = False
                st.rerun()
        with clo:
            if os.path.exists("logo.png"):
                st.image("logo.png", width=80)

    st.write("---")
    try:
        conn = get_sheet_connection()
        role = str(st.session_state["user_info"]["role"]).strip().title()
        if role == "Admin":
            st.title("لوحة القيادة التنفيذية")
            admin_view(conn, user_name)
        elif role == "Owner":
            owner_view(conn, user_name,
                       st.session_state["user_info"]["assigned_initiative"])
        elif role in ("Viewer", "Staff"):
            viewer_view(conn, user_name)
        else:
            st.error("الدور غير معروف: " + role)
    except Exception as e:
        st.error("خطأ غير متوقع: " + str(e))

st.markdown(
    '<div class="footer">System Version: 37.0 (NMCC - 2026)</div>',
    unsafe_allow_html=True,
)
