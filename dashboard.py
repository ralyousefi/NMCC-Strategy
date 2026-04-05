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
# 0. تهيئة حالة الجلسة (لتجنب KeyError)
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = {}

# ---------------------------------------------------------
# 1. إعدادات الصفحة والهوية البصرية
# ---------------------------------------------------------
st.set_page_config(page_title="نظام إدارة الاستراتيجية", layout="wide", page_icon="📊")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Tajawal', sans-serif; direction: rtl; }
    h1, h2, h3, h4, p, div, input, select, textarea, .stSelectbox, .stNumberInput {text-align: right;}
    .stDataFrame {direction: rtl;}
    div[data-testid="stMetric"] { background-color: #ffffff; border: 1px solid #e6e6e6; padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; }
    div[data-testid="stMetricLabel"] { font-size: 20px !important; color: #0068c9 !important; font-weight: bold !important; justify-content: center; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #0068c9; font-weight: bold; }
    .history-box { background-color: #eef5ff; padding: 15px; border-radius: 8px; border: 1px solid #d0e2ff; margin-top: 10px; margin-bottom: 20px; font-size: 15px; line-height: 1.6; white-space: pre-wrap; box-shadow: inset 0 0 5px rgba(0,0,0,0.05); }
    .history-title { color: #0068c9; font-weight: bold; margin-bottom: 5px; font-size: 16px; }
    .admin-alert-box { background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 8px; border: 1px solid #ffeeba; border-right: 5px solid #ffc107; margin-bottom: 20px; font-weight: bold; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f1f1f1; color: #555; text-align: center; padding: 10px; font-size: 12px; border-top: 1px solid #ddd; z-index: 100; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. الدوال المساعدة والبيانات
# ---------------------------------------------------------
KPI_GROUPS = {
    "QI4SD": ["QI4SD - Metrology", "CMC", "B of CMC", "ILC", "CC", "OIML project groups", "OIML-CS - number of services offered"],
    "البحث والتطوير": ["عدد الابحاث العلمية المنشورة في مجلات مصنفة دولياً Q1, Q2", "عدد المشاركات العلمية الدولية", "عدد الطلاب الملتحقين", "عدد فعاليات الاستقطاب الجامعي", "عدد المشاريع الوطنية", "عدد المشاركين سنوياً في برامج التبادل الفني"],
    "الكفاءة التشغيلية": ["نسبة نضج الحوكمة المؤسسية KAQA", "مؤشر التميز المؤسسي", "نسبة الإجراءات المؤتمتة", "مستوى رضا المستفيدين", "التحول الرقمي DGA", "نسبة الدوران الوظيفي", "نسبة الإيرادات الى إجمالي ميزانية", "نسبة النمو في إيرادات"]
}

def get_kpi_category(kpi_name):
    kpi_name = str(kpi_name).strip()
    for group, items in KPI_GROUPS.items():
        if kpi_name in [str(i).strip() for i in items]: return group
    return "مؤشرات أخرى"

SHEET_ID = "11tKfYa-Sqa96wDwQvMvChgRWaxgMRAWAIvul7p27ayY"

def get_creds():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if st.secrets is not None and 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if 'private_key' in creds_dict: creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
            return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except: pass
    json_key = "credentials.json"
    return ServiceAccountCredentials.from_json_keyfile_name(json_key, scope) if os.path.exists(json_key) else None

def get_sheet_connection():
    creds = get_creds()
    if not creds: st.error("⚠️ ملف الاعتمادات غير موجود!"); st.stop()
    return gspread.authorize(creds).open_by_key(SHEET_ID)

def safe_int(val):
    try: return int(float(str(val).replace('%', '').strip())) if str(val).strip() != '' else 0
    except: return 0

def safe_float(val):
    try: return float(str(val).replace('%', '').strip()) if str(val).strip() != '' else 0.0
    except: return 0.0

def clean_df_for_gspread(df):
    return df.fillna("").astype(object).where(pd.notnull(df), "")

def parse_date(date_str):
    try: return pd.to_datetime(date_str).date()
    except: return datetime.today().date()

def append_timestamped_comment(original_text, new_comment):
    if not new_comment or str(new_comment).strip() == "": return original_text
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = f"📅 {timestamp}: {str(new_comment).strip()}"
    return f"{str(original_text)}\n----------------\n{new_entry}" if original_text and str(original_text).strip() != "" else new_entry

# ---------------------------------------------------------
# 3. نظام تسجيل الدخول
# ---------------------------------------------------------
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
# 4. واجهة المدير (Admin) - مع التعديلات الجديدة
# ---------------------------------------------------------
def admin_view(sh, user_name):
    st.markdown("### 📊 لوحة القيادة التنفيذية")
    try:
        ws_acts = sh.worksheet("Activities")
        df_acts_raw = pd.DataFrame(ws_acts.get_all_records())
        
        # فلترة الإخفاء (Logical Delete) للمدير
        if 'is_deleted' in df_acts_raw.columns:
            df_acts = df_acts_raw[df_acts_raw['is_deleted'].astype(str).str.upper() != 'TRUE'].copy()
        else:
            df_acts = df_acts_raw.copy()

        if not df_acts.empty:
            df_acts['Progress'] = df_acts['Progress'].apply(safe_int)
            today = datetime.now().date()
            df_acts['End_Date_DT'] = pd.to_datetime(df_acts['End_Date'], errors='coerce').dt.date
            df_acts['Start_Date_DT'] = pd.to_datetime(df_acts['Start_Date'], errors='coerce').dt.date
            
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
                with st.spinner("جاري الحفظ..."):
                    for index, row in edited_df.iterrows():
                        if str(row['New_Admin_Note']).strip():
                            mask = (df_acts_raw['Mabadara'] == init) & (df_acts_raw['Activity'] == row['Activity'])
                            df_acts_raw.loc[mask, 'Admin_Comment'] = append_timestamped_comment(df_acts_raw.loc[mask, 'Admin_Comment'].values[0], row['New_Admin_Note'])
                    clean_data = clean_df_for_gspread(df_acts_raw)
                    ws_acts.update(values=[clean_data.columns.values.tolist()] + clean_data.values.tolist(), range_name='A1')
                    st.success("تم الحفظ!"); time.sleep(1); st.rerun()

        with tab2:
            ws_kpi = sh.worksheet("KPIs")
            df_kpi = pd.DataFrame(ws_kpi.get_all_records())
            # (هنا يمكن إضافة كود رسم المخططات البيانية للمؤشرات)
            st.info("تبويب المؤشرات قيد العرض")

        with tab3:
            st.markdown("#### ⚠️ الأنشطة المتعثرة في جميع المبادرات")
            today = datetime.now().date()
            late = df_acts[(df_acts['Progress'] < 100) & (df_acts['End_Date_DT'] < today)]
            not_started = df_acts[(df_acts['Progress'] == 0) & (df_acts['Start_Date_DT'] <= today)]
            
            if not late.empty:
                st.warning(f"🔴 أنشطة متأخرة ({len(late)})")
                st.dataframe(late[['Mabadara', 'Activity', 'End_Date', 'Progress', 'Owner_Comment']], hide_index=True, use_container_width=True)
            if not not_started.empty:
                st.info(f"🟡 حان موعد بدايتها ولم تبدأ ({len(not_started)})")
                st.dataframe(not_started[['Mabadara', 'Activity', 'Start_Date', 'Progress']], hide_index=True, use_container_width=True)
            if late.empty and not_started.empty: st.success("✅ لا توجد أنشطة متأخرة")

    except Exception as e: st.error(f"خطأ: {e}")

# ---------------------------------------------------------
# 5. واجهة المالك (Owner) - بدون أي تعديلات
# ---------------------------------------------------------
def owner_view(sh, user_name, my_initiatives_str):
    if my_initiatives_str:
        my_list = [x.strip() for x in str(my_initiatives_str).split(',') if x.strip() != '']
    else: my_list = []

    try:
        ws_acts = sh.worksheet("Activities")
        all_data = pd.DataFrame(ws_acts.get_all_records())
        my_data = all_data[all_data['Mabadara'].astype(str).str.strip().isin(my_list)].copy()
    except Exception as e: st.error(f"خطأ: {e}"); return

    tab1, tab2 = st.tabs(["📋 تحديث الأنشطة", "✏️ مؤشراتي"])
    with tab1:
        if not my_list: st.warning("لا توجد مبادرات")
        else:
            sel_init = st.selectbox("المبادرة", my_data['Mabadara'].unique())
            acts = my_data[my_data['Mabadara'] == sel_init]
            sel_act = st.selectbox("النشاط", acts['Activity'].unique())
            if sel_act:
                row = acts[acts['Activity'] == sel_act].iloc[0]
                with st.expander("⚙️ إعدادات (حذف نهائي)"):
                    if st.button("تأكيد الحذف من الملف نهائياً", type="primary"):
                        cell = ws_acts.find(sel_act)
                        if cell: ws_acts.delete_rows(cell.row); st.success("تم الحذف!"); st.rerun()

                with st.form("update_owner"):
                    new_prog = st.number_input("النسبة", 0, 100, safe_int(row['Progress']))
                    new_note = st.text_area("ملاحظة")
                    if st.form_submit_button("حفظ"):
                        mask = (all_data['Mabadara'] == sel_init) & (all_data['Activity'] == sel_act)
                        all_data.loc[mask, 'Progress'] = new_prog
                        all_data.loc[mask, 'Owner_Comment'] = append_timestamped_comment(row['Owner_Comment'], new_note)
                        ws_acts.update(values=[all_data.columns.values.tolist()] + clean_df_for_gspread(all_data).values.tolist(), range_name='A1')
                        st.success("تم!"); st.rerun()

# ---------------------------------------------------------
# 6. التشغيل الرئيسي
# ---------------------------------------------------------
if not st.session_state['logged_in']:
    login()
else:
    col_info, col_logout = st.columns([8, 2])
    with col_info: st.write(f"👤 {st.session_state['user_info']['name']} | {st.session_state['user_info']['role']}")
    with col_logout:
        if st.button("خروج"): st.session_state['logged_in'] = False; st.rerun()

    conn = get_sheet_connection()
    role = str(st.session_state['user_info']['role']).strip().lower()
    if role == 'admin': admin_view(conn, st.session_state['user_info']['name'])
    elif role == 'owner': owner_view(conn, st.session_state['user_info']['name'], st.session_state['user_info'].get('assigned_initiative', ''))

st.markdown('<div class="footer">Strategy Management System v32.0 - 2026</div>', unsafe_allow_html=True)
