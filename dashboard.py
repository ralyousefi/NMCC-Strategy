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
# 1. إعدادات الصفحة والهوية البصرية (كما هي)
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
# 2. تعريف المجموعات والدوال المساعدة (كما هي)
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
    return ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope) if os.path.exists("credentials.json") else None

def get_sheet_connection():
    creds = get_creds()
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
# 3. واجهة المدير (Admin) - النسخة المحدثة مع التبويب الثالث
# ---------------------------------------------------------
def admin_view(sh, user_name):
    st.markdown("### 📊 لوحة القيادة التنفيذية")
    try:
        ws_acts = sh.worksheet("Activities")
        df_acts_raw = pd.DataFrame(ws_acts.get_all_records())
        
        # فلترة الأنشطة التي لم تُحذف منطقياً (بناءً على عمود is_deleted)
        if 'is_deleted' in df_acts_raw.columns:
            df_acts = df_acts_raw[df_acts_raw['is_deleted'].astype(str).str.upper() != 'TRUE'].copy()
        else:
            df_acts = df_acts_raw.copy()

        if not df_acts.empty:
            df_acts['Progress'] = df_acts['Progress'].apply(safe_int)
            total_initiatives = df_acts['Mabadara'].nunique()
            total_activities = len(df_acts)
            avg_progress = df_acts['Progress'].mean()
            
            today = datetime.now().date()
            df_acts['End_Date_DT'] = pd.to_datetime(df_acts['End_Date'], errors='coerce').dt.date
            df_acts['Start_Date_DT'] = pd.to_datetime(df_acts['Start_Date'], errors='coerce').dt.date
            
            delayed_count = len(df_acts[(df_acts['Progress'] < 100) & (df_acts['End_Date_DT'] < today)])

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("📦 المبادرات", total_initiatives)
            k2.metric("📝 الأنشطة", total_activities)
            k3.metric("📈 متوسط الإنجاز", f"{avg_progress:.1f}%")
            k4.metric("🚨 أنشطة متأخرة", delayed_count, delta_color="inverse")
            st.markdown("---")

        tab1, tab2, tab3 = st.tabs(["📋 تفاصيل المبادرات", "📊 مؤشرات الأداء (المجموعات)", "🚨 الأنشطة المتأخرة والمتابعة"])
        
        with tab1:
            if not df_acts.empty:
                init = st.selectbox("اختر المبادرة:", df_acts['Mabadara'].unique())
                df_filt = df_acts[df_acts['Mabadara'] == init].copy()
                df_filt['New_Admin_Note'] = ""
                
                edited_df = st.data_editor(df_filt, column_config={
                    "Activity": st.column_config.TextColumn("النشاط", width="large"),
                    "Progress": st.column_config.ProgressColumn("الإنجاز %", format="%d%%"),
                    "New_Admin_Note": st.column_config.TextColumn("✍️ ملاحظة إدارية جديدة", width="large"),
                    "End_Date_DT": None, "Start_Date_DT": None, "is_deleted": None, "Mabadara": None
                }, disabled=["Activity", "Progress", "Owner_Comment", "Admin_Comment", "Start_Date", "End_Date"], hide_index=True, use_container_width=True)

                if st.button("💾 حفظ الملاحظات الجديدة (أنشطة)"):
                    with st.spinner("جاري الحفظ..."):
                        # التحديث يتم على df_acts_raw لضمان بقاء الأسطر المخفية في الملف
                        for index, row in edited_df.iterrows():
                            if str(row['New_Admin_Note']).strip():
                                mask = (df_acts_raw['Mabadara'] == row['Mabadara']) & (df_acts_raw['Activity'] == row['Activity'])
                                df_acts_raw.loc[mask, 'Admin_Comment'] = append_timestamped_comment(df_acts_raw.loc[mask, 'Admin_Comment'].values[0], row['New_Admin_Note'])
                        clean_data = clean_df_for_gspread(df_acts_raw)
                        ws_acts.update(values=[clean_data.columns.values.tolist()] + clean_data.values.tolist(), range_name='A1')
                        st.success("✅ تم الحفظ!")
                        time.sleep(1); st.rerun()

        with tab2:
            ws_kpi = sh.worksheet("KPIs")
            df_kpi = pd.DataFrame(ws_kpi.get_all_records())
            display_kpi_layout(df_kpi)

        with tab3:
            st.markdown("#### ⚠️ أنشطة تتطلب إجراء فوري (جميع المبادرات)")
            today = datetime.now().date()
            df_late = df_acts[(df_acts['Progress'] < 100) & (df_acts['End_Date_DT'] < today)].copy()
            df_not_started = df_acts[(df_acts['Progress'] == 0) & (df_acts['Start_Date_DT'] <= today)].copy()
            
            if not df_late.empty:
                st.warning(f"🔴 أنشطة متأخرة تجاوزت موعد التسليم ({len(df_late)})")
                st.dataframe(df_late[['Mabadara', 'Activity', 'End_Date', 'Progress', 'Owner_Comment']], hide_index=True, use_container_width=True)
            if not df_not_started.empty:
                st.info(f"🟡 أنشطة حان موعد بدايتها ولم تبدأ ({len(df_not_started)})")
                st.dataframe(df_not_started[['Mabadara', 'Activity', 'Start_Date', 'Progress']], hide_index=True, use_container_width=True)
            if df_late.empty and df_not_started.empty: st.success("✅ لا توجد أنشطة متأخرة حالياً.")

    except Exception as e: st.error(f"خطأ: {e}")

# ---------------------------------------------------------
# 4. واجهة المالك (Owner) - بقيت كما هي في الكود الأصلي تماماً
# ---------------------------------------------------------
def owner_view(sh, user_name, my_initiatives_str):
    if my_initiatives_str:
        my_list = [x.strip() for x in str(my_initiatives_str).split(',') if x.strip() != '']
    else:
        my_list = []

    try:
        ws_acts = sh.worksheet("Activities")
        all_data = pd.DataFrame(ws_acts.get_all_records())
        all_data['Mabadara'] = all_data['Mabadara'].astype(str).str.strip()
        all_data['Activity'] = all_data['Activity'].astype(str).str.strip()
        if 'Admin_Comment' not in all_data.columns: all_data['Admin_Comment'] = ""
        if 'Owner_Comment' not in all_data.columns: all_data['Owner_Comment'] = ""
        
        my_data = all_data[all_data['Mabadara'].isin(my_list)].copy()

        ws_kpi = sh.worksheet("KPIs")
        df_kpi = pd.DataFrame(ws_kpi.get_all_records())
        for col in ['Admin_Comment', 'Owner_Comment', 'Owner']:
            if col not in df_kpi.columns: df_kpi[col] = ""
        df_kpi['Target'] = df_kpi['Target'].apply(safe_float)
        df_kpi['Actual'] = df_kpi['Actual'].apply(safe_float)
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {e}"); return

    tab1, tab2, tab3 = st.tabs(["📋 تحديث الأنشطة", "✏️ تحديث مؤشراتي", "📊 كافة المؤشرات (للاطلاع)"])

    with tab1:
        st.markdown("### 📌 تحديث أنشطة المبادرات")
        if not my_list: st.warning("⚠️ لا توجد مبادرات مسندة إليك.")
        else:
            sel_init = st.selectbox("اختر المبادرة", my_data['Mabadara'].unique())
            with st.expander("➕ إضافة نشاط جديد لهذه المبادرة"):
                with st.form("add_activity_form"):
                    new_act_name = st.text_input("اسم النشاط الجديد")
                    c_new1, c_new2 = st.columns(2)
                    with c_new1: new_act_start = st.date_input("البداية", key="new_start")
                    with c_new2: new_act_end = st.date_input("النهاية", key="new_end")
                    if st.form_submit_button("إضافة النشاط"):
                        if new_act_name.strip() == "": st.error("الرجاء كتابة اسم النشاط")
                        else:
                            try:
                                ws_acts.append_row([sel_init, new_act_name, str(new_act_start), str(new_act_end), 0, "", "", ""])
                                st.success("تمت الإضافة!"); time.sleep(1); st.rerun()
                            except Exception as e: st.error(f"خطأ: {e}")

            acts_in_init = my_data[my_data['Mabadara'] == sel_init]
            if not acts_in_init.empty:
                sel_act_name = st.selectbox("النشاط", acts_in_init['Activity'].unique())
                if sel_act_name:
                    row = acts_in_init[acts_in_init['Activity'] == sel_act_name].iloc[0]
                    with st.expander("⚙️ إعدادات النشاط (تعديل الاسم / حذف)"):
                        c_edit, c_delete = st.columns(2)
                        with c_edit:
                            new_name_val = st.text_input("الاسم الجديد", value=sel_act_name)
                            if st.button("تحديث الاسم"):
                                cell = ws_acts.find(sel_act_name)
                                if cell: ws_acts.update_cell(cell.row, cell.col, new_name_val); st.success("تم!"); st.rerun()
                        with c_delete:
                            if st.button("تأكيد الحذف النهائي", type="primary"):
                                cell_del = ws_acts.find(sel_act_name)
                                if cell_del: ws_acts.delete_rows(cell_del.row); st.success("تم الحذف!"); st.rerun()

                    with st.form("update_form"):
                        col_start, col_end, col_prog = st.columns(3)
                        new_start = col_start.date_input("البداية", value=parse_date(row['Start_Date']))
                        new_end = col_end.date_input("النهاية", value=parse_date(row['End_Date']))
                        new_prog = col_prog.number_input("نسبة الإنجاز %", 0, 100, value=safe_int(row['Progress']))
                        ext_link = st.text_input("رابط الدليل", value=str(row['Evidence_Link']))
                        new_note = st.text_area("إضافة ملاحظة جديدة")
                        if st.form_submit_button("💾 حفظ التحديث"):
                            mask = (all_data['Mabadara'] == sel_init) & (all_data['Activity'] == sel_act_name)
                            all_data.loc[mask, ['Progress', 'Start_Date', 'End_Date', 'Evidence_Link']] = [new_prog, str(new_start), str(new_end), ext_link]
                            all_data.loc[mask, 'Owner_Comment'] = append_timestamped_comment(row['Owner_Comment'], new_note)
                            ws_acts.update(values=[all_data.columns.values.tolist()] + clean_df_for_gspread(all_data).values.tolist(), range_name='A1')
                            st.success("تم التحديث!"); time.sleep(1); st.rerun()

    with tab2: # (كود تحديث المؤشرات للمالك كما هو)
        st.markdown("### 📈 تحديث مؤشرات الأداء")
        # ... بقية كود الـ Owner ...
        pass
    with tab3: display_kpi_layout(df_kpi)

# ---------------------------------------------------------
# 5. بقية أجزاء الكود (Login, Viewer, Main Loop) كما هي
# ---------------------------------------------------------
def display_kpi_layout(df_all):
    df_all['Category'] = df_all['KPI_Name'].apply(get_kpi_category)
    col1, col2 = st.columns(2)
    with col1: plot_group_barchart(df_all[df_all['Category'] == "QI4SD"], "مجموعة QI4SD")
    with col2: plot_group_barchart(df_all[df_all['Category'] == "البحث والتطوير"], "مجموعة البحث والتطوير")
    st.markdown("---")
    plot_group_barchart(df_all[df_all['Category'] == "الكفاءة التشغيلية"], "مجموعة الكفاءة التشغيلية")

def plot_group_barchart(df, title):
    if df.empty: return
    df['Actual'] = df['Actual'].apply(safe_float)
    df['Target'] = df['Target'].apply(safe_float)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['KPI_Name'], y=df['Actual'], name='الفعلي', marker_color='#1f77b4'))
    fig.add_trace(go.Scatter(x=df['KPI_Name'], y=df['Target'], mode='markers', name='المستهدف', marker=dict(symbol='line-ew', size=30, color='black')))
    fig.update_layout(title=title, barmode='group')
    st.plotly_chart(fig, use_container_width=True)

# Main Execution
if not st.session_state['logged_in']:
    login()
else:
    sh = get_sheet_connection()
    role = str(st.session_state['user_info']['role']).strip().lower()
    if role == 'admin': admin_view(sh, st.session_state['user_info']['name'])
    elif role == 'owner': owner_view(sh, st.session_state['user_info']['name'], st.session_state['user_info'].get('assigned_initiative', ''))
    st.markdown('<div class="footer">System Version: 32.0 (NMCC - 2026)</div>', unsafe_allow_html=True)
