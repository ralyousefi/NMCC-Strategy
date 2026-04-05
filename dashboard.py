import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import time
from datetime import datetime

# ---------------------------------------------------------
# 1. إعدادات الصفحة والهوية البصرية
# ---------------------------------------------------------
st.set_page_config(page_title="نظام إدارة الاستراتيجية", layout="wide", page_icon="📊")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
    }
    
    h1, h2, h3, h4, p, div, input, select, textarea, .stSelectbox, .stNumberInput {text-align: right;}
    .stDataFrame {direction: rtl;}
    
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e6e6e6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 20px !important;      
        color: #0068c9 !important;        
        font-weight: bold !important;    
        justify-content: center;
    }

    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #0068c9;
        font-weight: bold;
    }
    
    .history-box {
        background-color: #eef5ff;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #d0e2ff;
        margin-top: 10px;
        margin-bottom: 20px;
        font-size: 15px;
        line-height: 1.6;
        white-space: pre-wrap;
        box-shadow: inset 0 0 5px rgba(0,0,0,0.05);
    }
    
    .history-title {
        color: #0068c9;
        font-weight: bold;
        margin-bottom: 5px;
        font-size: 16px;
    }

    .admin-alert-box {
        background-color: #fff3cd;
        color: #856404;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #ffeeba;
        border-right: 5px solid #ffc107;
        margin-bottom: 20px;
        font-weight: bold;
    }

    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f1f1f1;
        color: #555;
        text-align: center;
        padding: 10px;
        font-size: 12px;
        border-top: 1px solid #ddd;
        z-index: 100;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. تعريف المجموعات (Categorization)
# ---------------------------------------------------------
KPI_GROUPS = {
    "QI4SD": ["QI4SD - Metrology", "CMC", "B of CMC", "ILC", "CC", "OIML project groups", "OIML-CS - number of services offered"],
    "البحث والتطوير": ["عدد الابحاث العلمية المنشورة في مجلات مصنفة دولياً Q1, Q2", "عدد المشاركات العلمية الدولية", "عدد الطلاب الملتحقين", "عدد فعاليات الاستقطاب الجامعي", "عدد المشاريع الوطنية", "عدد المشاركين سنوياً في برامج التبادل الفني"],
    "الكفاءة التشغيلية": ["نسبة نضج الحوكمة المؤسسية KAQA", "مؤشر التميز المؤسسي", "نسبة الإجراءات المؤتمتة", "مستوى رضا المستفيدين", "التحول الرقمي DGA", "نسبة الدوران الوظيفي", "نسبة الإيرادات الى إجمالي ميزانية", "نسبة النمو في إيرادات"]
}

def get_kpi_category(kpi_name):
    kpi_name = str(kpi_name).strip()
    for group, items in KPI_GROUPS.items():
        clean_items = [str(i).strip() for i in items]
        if kpi_name in clean_items: return group
    return "مؤشرات أخرى"

# ---------------------------------------------------------
# 3. إعدادات الاتصال والدوال المساعدة
# ---------------------------------------------------------
SHEET_ID = "11tKfYa-Sqa96wDwQvMvChgRWaxgMRAWAIvul7p27ayY"

def get_creds():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if st.secrets is not None and 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if 'private_key' in creds_dict:
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
            return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception: pass
    json_key_file = "credentials.json"
    if os.path.exists(json_key_file):
        return ServiceAccountCredentials.from_json_keyfile_name(json_key_file, scope)
    st.error("⚠️ خطأ في الاتصال: لم يتم العثور على ملف الاعتمادات أو Secrets.")
    st.stop()

def get_sheet_connection():
    creds = get_creds()
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

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
    return f"{str(original_text)}\n----------------\n{new_entry}" if original_text and str(original_text).strip() != "" else new_entry

# ---------------------------------------------------------
# 4. نظام تسجيل الدخول
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_info'] = {}

def login():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h2 style='text-align: center;'>🔐 تسجيل الدخول</h2>", unsafe_allow_html=True)
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("دخول", use_container_width=True):
            try:
                sh = get_sheet_connection()
                users_df = pd.DataFrame(sh.worksheet("Users").get_all_records())
                user = users_df[users_df['username'].astype(str).str.strip() == username.strip()]
                if not user.empty and str(user.iloc[0]['password']) == str(password):
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user.iloc[0].to_dict()
                    st.rerun()
                else: st.error("بيانات الدخول غير صحيحة")
            except Exception as e: st.error(f"خطأ اتصال: {e}")

# ---------------------------------------------------------
# 5. دوال الرسوم البيانية
# ---------------------------------------------------------
def plot_group_barchart(df, group_title):
    if df.empty:
        st.info(f"لا توجد مؤشرات في مجموعة: {group_title}")
        return
    def get_color(row):
        target, actual = row['Target'], row['Actual']
        direction = str(row.get('Direction', 'تصاعدي')).strip()
        if direction == 'تنازلي': return "#2ca02c" if actual <= target else "#d62728"
        else: return "#2ca02c" if actual >= target else "#d62728"
    df['Color'] = df.apply(get_color, axis=1)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['KPI_Name'], y=df['Actual'], marker_color=df['Color'], text=df['Actual'], textposition='auto'))
    fig.add_trace(go.Scatter(x=df['KPI_Name'], y=df['Target'], mode='markers', name='المستهدف', marker=dict(symbol='line-ew', size=40, color='black')))
    fig.update_layout(title=dict(text=f"📊 {group_title}", x=0.5), barmode='overlay', legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center'))
    st.plotly_chart(fig, use_container_width=True)

def display_kpi_layout(df_all):
    df_all['Category'] = df_all['KPI_Name'].apply(get_kpi_category)
    col1, col2 = st.columns(2)
    with col1: plot_group_barchart(df_all[df_all['Category'] == "QI4SD"], "مجموعة QI4SD")
    with col2: plot_group_barchart(df_all[df_all['Category'] == "البحث والتطوير"], "مجموعة البحث والتطوير")
    st.markdown("---")
    plot_group_barchart(df_all[df_all['Category'] == "الكفاءة التشغيلية"], "مجموعة الكفاءة التشغيلية")

# ---------------------------------------------------------
# 6. واجهات المستخدمين
# ---------------------------------------------------------

# --- واجهة المدير ---
def admin_view(sh, user_name):
    st.markdown("### 📊 لوحة القيادة التنفيذية")
    try:
        ws_acts = sh.worksheet("Activities")
        df_acts_raw = pd.DataFrame(ws_acts.get_all_records())
        
        # فلترة المحذوف (Logical Delete)
        if 'is_deleted' in df_acts_raw.columns:
            df_acts = df_acts_raw[df_acts_raw['is_deleted'].astype(str).str.upper() != 'TRUE'].copy()
        else:
            df_acts = df_acts_raw.copy()

        if not df_acts.empty:
            df_acts['Progress'] = df_acts['Progress'].apply(safe_int)
            df_acts['End_Date_DT'] = pd.to_datetime(df_acts['End_Date'], errors='coerce').dt.date
            df_acts['Start_Date_DT'] = pd.to_datetime(df_acts['Start_Date'], errors='coerce').dt.date
            today = datetime.now().date()
            
            delayed_count = len(df_acts[(df_acts['Progress'] < 100) & (df_acts['End_Date_DT'] < today)])
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("📦 المبادرات", df_acts['Mabadara'].nunique())
            k2.metric("📝 الأنشطة", len(df_acts))
            k3.metric("📈 متوسط الإنجاز", f"{df_acts['Progress'].mean():.1f}%")
            k4.metric("🚨 أنشطة متأخرة", delayed_count, delta_color="inverse")
            st.markdown("---")

        tab1, tab2, tab3 = st.tabs(["📋 تفاصيل المبادرات", "📊 مؤشرات الأداء", "🚨 الأنشطة المتأخرة والمتابعة"])

        with tab1:
            init = st.selectbox("اختر المبادرة:", df_acts['Mabadara'].unique())
            df_filt = df_acts[df_acts['Mabadara'] == init].copy()
            df_filt['New_Admin_Note'] = ""
            edited_df = st.data_editor(df_filt, column_config={
                "Activity": st.column_config.TextColumn("النشاط", width="large"),
                "Progress": st.column_config.ProgressColumn("الإنجاز %", format="%d%%"),
                "New_Admin_Note": st.column_config.TextColumn("✍️ ملاحظة جديدة", width="large"),
                "is_deleted": None, "End_Date_DT": None, "Start_Date_DT": None, "Mabadara": None
            }, disabled=["Activity", "Progress", "Owner_Comment", "Admin_Comment", "Start_Date", "End_Date"], use_container_width=True, hide_index=True)
            
            if st.button("💾 حفظ ملاحظات المدير"):
                # منطق الحفظ (مدمج مع سجل الملاحظات)
                with st.spinner("جاري الحفظ..."):
                    df_full = pd.DataFrame(ws_acts.get_all_records())
                    for _, row in edited_df.iterrows():
                        if row['New_Admin_Note'].strip():
                            mask = (df_full['Mabadara'] == init) & (df_full['Activity'] == row['Activity'])
                            df_full.loc[mask, 'Admin_Comment'] = append_timestamped_comment(df_full.loc[mask, 'Admin_Comment'].values[0], row['New_Admin_Note'])
                    ws_acts.update(values=[df_full.columns.values.tolist()] + clean_df_for_gspread(df_full).values.tolist(), range_name='A1')
                    st.success("تم الحفظ!")
                    st.rerun()

        with tab2:
            df_kpi = pd.DataFrame(sh.worksheet("KPIs").get_all_records())
            df_kpi['Target'] = df_kpi['Target'].apply(safe_float)
            df_kpi['Actual'] = df_kpi['Actual'].apply(safe_float)
            display_kpi_layout(df_kpi)

        with tab3:
            st.markdown("#### ⚠️ الأنشطة المتعثرة في جميع المبادرات")
            today = datetime.now().date()
            late = df_acts[(df_acts['Progress'] < 100) & (df_acts['End_Date_DT'] < today)]
            not_started = df_acts[(df_acts['Progress'] == 0) & (df_acts['Start_Date_DT'] <= today)]
            
            if not late.empty:
                st.warning(f"🔴 أنشطة تجاوزت موعد التسليم ({len(late)})")
                st.dataframe(late[['Mabadara', 'Activity', 'End_Date', 'Progress', 'Owner_Comment']], use_container_width=True, hide_index=True)
            if not not_started.empty:
                st.info(f"🟡 أنشطة حان موعد بدايتها ولم تبدأ ({len(not_started)})")
                st.dataframe(not_started[['Mabadara', 'Activity', 'Start_Date', 'Progress']], use_container_width=True, hide_index=True)
            if late.empty and not_started.empty: st.success("كل الأنشطة تسير وفق الجدول الزمني ✅")

    except Exception as e: st.error(f"خطأ: {e}")

# --- واجهة المالك (مع ميزة الإخفاء بدلاً من الحذف) ---
def owner_view(sh, user_name, my_initiatives_str):
    my_list = [x.strip() for x in str(my_initiatives_str).split(',') if x.strip() != '']
    try:
        ws_acts = sh.worksheet("Activities")
        df_acts_all = pd.DataFrame(ws_acts.get_all_records())
        
        # فلترة المحذوف
        if 'is_deleted' in df_acts_all.columns:
            my_data = df_acts_all[(df_acts_all['Mabadara'].isin(my_list)) & (df_acts_all['is_deleted'].astype(str).str.upper() != 'TRUE')].copy()
        else:
            my_data = df_acts_all[df_acts_all['Mabadara'].isin(my_list)].copy()

        tab1, tab2 = st.tabs(["📋 تحديث الأنشطة", "📈 تحديث مؤشراتي"])
        
        with tab1:
            if my_data.empty: st.warning("لا توجد مبادرات مسندة")
            else:
                sel_init = st.selectbox("المبادرة", my_data['Mabadara'].unique())
                acts = my_data[my_data['Mabadara'] == sel_init]
                sel_act = st.selectbox("النشاط", acts['Activity'].unique())
                
                if sel_act:
                    row = acts[acts['Activity'] == sel_act].iloc[0]
                    with st.expander("🗑️ إخفاء النشاط من لوحة التحكم"):
                        if st.button("تأكيد الإخفاء (سيتم حفظه في ملف البيانات فقط)", type="primary"):
                            cell = ws_acts.find(sel_act)
                            headers = ws_acts.row_values(1)
                            if 'is_deleted' in headers:
                                ws_acts.update_cell(cell.row, headers.index('is_deleted') + 1, "TRUE")
                                st.success("تم الإخفاء")
                                time.sleep(1)
                                st.rerun()
                            else: st.error("عمود is_deleted غير موجود في الشيت")

                    with st.form("update_act"):
                        new_prog = st.slider("نسبة الإنجاز", 0, 100, safe_int(row['Progress']))
                        new_note = st.text_area("إضافة ملاحظة")
                        if st.form_submit_button("حفظ التحديث"):
                            df_full = pd.DataFrame(ws_acts.get_all_records())
                            mask = (df_full['Mabadara'] == sel_init) & (df_full['Activity'] == sel_act)
                            df_full.loc[mask, 'Progress'] = new_prog
                            df_full.loc[mask, 'Owner_Comment'] = append_timestamped_comment(df_full.loc[mask, 'Owner_Comment'].values[0], new_note)
                            ws_acts.update(values=[df_full.columns.values.tolist()] + clean_df_for_gspread(df_full).values.tolist(), range_name='A1')
                            st.success("تم التحديث")
                            st.rerun()
        with tab2: st.info("استخدم هذه المساحة لتحديث مؤشرات الأداء الخاصة بك (KPIs)")
    except Exception as e: st.error(f"خطأ: {e}")

# ---------------------------------------------------------
# 7. التشغيل الرئيسي
# ---------------------------------------------------------
if not st.session_state['logged_in']:
    login()
else:
    col_info, col_logout = st.columns([8, 2])
    with col_info: st.markdown(f"### 👤 {st.session_state['user_info']['name']} | دور: {st.session_state['user_info']['role']}")
    with col_logout:
        if st.button("تسجيل الخروج"):
            st.session_state['logged_in'] = False
            st.rerun()

    conn = get_sheet_connection()
    role = str(st.session_state['user_info']['role']).strip().lower()
    
    if role == 'admin': admin_view(conn, st.session_state['user_info']['name'])
    elif role == 'owner': owner_view(conn, st.session_state['user_info']['name'], st.session_state['user_info'].get('assigned_initiative', ''))
    else: st.warning("نسخة العرض فقط")

st.markdown('<div class="footer">Strategy Management System v3.1 - 2026</div>', unsafe_allow_html=True)
