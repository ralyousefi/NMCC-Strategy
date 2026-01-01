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

    .activity-box {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-right: 6px solid #0068c9;
        margin: 20px 0;
        font-size: 18px;
        line-height: 1.8;
        color: #0e1117;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* تنسيق صندوق الملاحظات التاريخية */
    .history-box {
        background-color: #eef5ff;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #d0e2ff;
        margin-bottom: 10px;
        font-size: 14px;
        white-space: pre-wrap; /* للحفاظ على الأسطر الجديدة */
        max-height: 200px;
        overflow-y: auto;
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
    
    .step-header {
        color: #0068c9;
        font-size: 16px;
        margin-bottom: 10px;
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
# 2. إعدادات الاتصال
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
    except Exception:
        pass
    json_key_file = "credentials.json"
    if os.path.exists(json_key_file):
        return ServiceAccountCredentials.from_json_keyfile_name(json_key_file, scope)
    st.error("⚠️ خطأ في الاتصال: لم يتم العثور على ملف الاعتمادات أو Secrets.")
    st.stop()

def get_sheet_connection():
    creds = get_creds()
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

# --- دوال مساعدة ---
def safe_int(val):
    try:
        if str(val).strip() == '': return 0
        return int(float(str(val).replace('%', '').strip()))
    except:
        return 0

def safe_float(val):
    try:
        if str(val).strip() == '': return 0.0
        return float(str(val).replace('%', '').strip())
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

# --- دالة إضافة التاريخ للملاحظات (الجديدة) ---
def append_timestamped_comment(original_text, new_comment):
    if not new_comment or new_comment.strip() == "":
        return original_text
    
    timestamp = datetime.now().strftime("%Y-%m-%d")
    new_entry = f"📅 {timestamp}: {new_comment.strip()}"
    
    if original_text and str(original_text).strip() != "":
        return f"{str(original_text)}\n----------------\n{new_entry}"
    else:
        return new_entry

# ---------------------------------------------------------
# 3. نظام تسجيل الدخول
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_info'] = {}

def login():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h2 style='text-align: center;'>🔐 تسجيل الدخول</h2>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("دخول", use_container_width=True):
            try:
                sh = get_sheet_connection()
                users_df = pd.DataFrame(sh.worksheet("Users").get_all_records())
                users_df['username'] = users_df['username'].astype(str).str.strip()
                user = users_df[users_df['username'] == username.strip()]
                
                if not user.empty and str(user.iloc[0]['password']) == str(password):
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("بيانات الدخول غير صحيحة")
            except Exception as e:
                st.error(f"خطأ اتصال: {e}")

# ---------------------------------------------------------
# 4. واجهات المستخدمين
# ---------------------------------------------------------

# --- دالة رسم المؤشرات (مشتركة) ---
def draw_kpi_chart(df):
    def get_status(row):
        target, actual = row['Target'], row['Actual']
        direction = row.get('Direction', 'تصاعدي') 
        if direction == 'تنازلي': 
            return "متقدم (أزرق)" if actual < target else "متحقق (أخضر)" if actual == target else "متأخر (أحمر)"
        else: 
            return "متقدم (أزرق)" if actual > target else "متحقق (أخضر)" if actual == target else "متأخر (أحمر)"

    df['Status'] = df.apply(get_status, axis=1)
    
    fig = go.Figure()
    status_colors = df['Status'].map({
        "متقدم (أزرق)": "#1f77b4", "متحقق (أخضر)": "#2ca02c", "متأخر (أحمر)": "#d62728"
    }).fillna("grey")

    fig.add_trace(go.Bar(
        x=df['KPI_Name'], y=df['Actual'], name='الفعلي', 
        marker_color=status_colors, text=df['Actual'],       
        textposition='inside', width=0.5                        
    ))
    fig.add_trace(go.Scatter(
        x=df['KPI_Name'], y=df['Target'], mode='markers',                  
        name='المستهدف', marker=dict(symbol='line-ew', size=50, color='black', line=dict(width=3)), 
    ))
    fig.update_layout(
        title="مقارنة الأداء (الفعلي vs المستهدف)", xaxis_title="المؤشر", yaxis_title="القيمة",
        barmode='overlay', bargap=0.4, legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center')
    )
    st.plotly_chart(fig, use_container_width=True)

# ================================
# واجهة المدير (Admin)
# ================================
def admin_view(sh, user_name):
    st.markdown("### 📊 نظرة عامة (لوحة القيادة)")
    
    try:
        ws_acts = sh.worksheet("Activities")
        df_acts = pd.DataFrame(ws_acts.get_all_records())
        
        if not df_acts.empty:
            df_acts['Progress'] = df_acts['Progress'].apply(safe_int)
            total_initiatives = df_acts['Mabadara'].nunique()
            total_activities = len(df_acts)
            avg_progress = df_acts['Progress'].mean()
            
            today = datetime.now().date()
            df_acts['End_Date_DT'] = pd.to_datetime(df_acts['End_Date'], errors='coerce').dt.date
            delayed_count = len(df_acts[(df_acts['Progress'] < 100) & (df_acts['End_Date_DT'] < today)])

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("📦 المبادرات", total_initiatives)
            k2.metric("📝 الأنشطة", total_activities)
            k3.metric("📈 متوسط الإنجاز", f"{avg_progress:.1f}%")
            k4.metric("🚨 أنشطة متأخرة", delayed_count, delta_color="inverse")

            st.markdown("---")
    except Exception as e:
        st.error(f"خطأ في تحميل الملخص: {e}")

    tab1, tab2 = st.tabs(["📋 تفاصيل المبادرات", "📊 مؤشرات الأداء (KPIs)"])
    
    with tab1:
        try:
            if 'Admin_Comment' not in df_acts.columns: df_acts['Admin_Comment'] = ""
            if not df_acts.empty:
                st.markdown("#### 🔎 مراجعة وتحديث المبادرات")
                init = st.selectbox("اختر المبادرة:", df_acts['Mabadara'].unique())
                filt = df_acts[df_acts['Mabadara'] == init]
                
                # ملاحظة: المحرر هنا يقوم بالكتابة فوق البيانات، لذا سنترك التحديث للمدير كما هو 
                # أو يمكننا إضافة عمود لعرض تاريخ التحديثات إذا رغبت مستقبلاً.
                edited_acts = st.data_editor(
                    filt,
                    column_config={
                        "Evidence_Link": st.column_config.LinkColumn("رابط الدليل", display_text="📎 فتح"),
                        "Progress": st.column_config.ProgressColumn("الإنجاز %", format="%d%%", min_value=0, max_value=100),
                        "Admin_Comment": st.column_config.TextColumn("ملاحظات المدير", width="medium"),
                        "Owner_Comment": st.column_config.TextColumn("رد الموظف (سجل)", disabled=True),
                        "End_Date_DT": None 
                    },
                    disabled=["Mabadara", "Activity", "Start_Date", "End_Date", "Progress", "Evidence_Link", "Owner_Comment"],
                    use_container_width=True,
                    key="admin_editor",
                    num_rows="fixed"
                )
                
                if st.button("💾 حفظ الملاحظات على المبادرات"):
                    with st.spinner("جاري الحفظ..."):
                        if 'End_Date_DT' in df_acts.columns: df_acts = df_acts.drop(columns=['End_Date_DT'])
                        for index, row in edited_acts.iterrows():
                            mask = (df_acts['Mabadara'] == row['Mabadara']) & (df_acts['Activity'] == row['Activity'])
                            # هنا المدير يكتب مباشرة، يمكن تطويره ليحفظ التاريخ أيضاً إذا رغبت
                            df_acts.loc[mask, 'Admin_Comment'] = row['Admin_Comment']
                        
                        clean_data = clean_df_for_gspread(df_acts)
                        ws_acts.update(values=[clean_data.columns.values.tolist()] + clean_data.values.tolist(), range_name='A1')
                        st.success("✅ تم الحفظ!")
                        time.sleep(1)
                        st.rerun()
        except Exception as e:
            st.error(f"خطأ تحميل: {e}")

    with tab2:
        try:
            ws_kpi = sh.worksheet("KPIs")
            df_kpi = pd.DataFrame(ws_kpi.get_all_records())
            
            # التأكد من وجود الأعمدة
            if 'Admin_Comment' not in df_kpi.columns: df_kpi['Admin_Comment'] = ""
            if 'Owner_Comment' not in df_kpi.columns: df_kpi['Owner_Comment'] = "" # العمود الجديد
            if 'Owner' not in df_kpi.columns: df_kpi['Owner'] = ""
            
            df_kpi['Target'] = df_kpi['Target'].apply(safe_float)
            df_kpi['Actual'] = df_kpi['Actual'].apply(safe_float)
            
            st.markdown("#### ✏️ إدارة المؤشرات")
            st.info("💡 بصفتك مديراً: يمكنك تعديل (المستهدف) ووضع (ملاحظات). تظهر ملاحظات المالك في العمود المخصص.")

            edited_kpi = st.data_editor(
                df_kpi, 
                num_rows="dynamic", 
                use_container_width=True, 
                key="kpi_editor_admin",
                column_config={
                     "Admin_Comment": st.column_config.TextColumn("ملاحظات المدير", width="medium"),
                     "Owner_Comment": st.column_config.TextColumn("ملاحظات مالك المؤشر", disabled=True, width="medium"), # للعرض فقط
                     "Actual": st.column_config.NumberColumn("المتحقق (Actual)", disabled=True), 
                     "Target": st.column_config.NumberColumn("المستهدف (Target)"), 
                     "Owner": st.column_config.TextColumn("المسؤول (Owner)"),
                }
            )
            
            if st.button("حفظ تحديثات المؤشرات"):
                clean_data = clean_df_for_gspread(edited_kpi)
                ws_kpi.update(values=[clean_data.columns.values.tolist()] + clean_data.values.tolist(), range_name='A1')
                st.success("تم الحفظ!")
                time.sleep(1)
                st.rerun()
            
            if not edited_kpi.empty:
                draw_kpi_chart(edited_kpi)
                
        except Exception as e:
            st.error(f"خطأ KPI: {e}")

# ================================
# واجهة المالك (Owner) - محدثة مع التاريخ والملاحظات
# ================================
def owner_view(sh, user_name, my_initiatives_str):
    if my_initiatives_str:
        my_list = [x.strip() for x in str(my_initiatives_str).split(',') if x.strip() != '']
    else:
        my_list = []

    # --- الجزء 1: تحديث أنشطة المبادرات ---
    try:
        ws_acts = sh.worksheet("Activities")
        all_data = pd.DataFrame(ws_acts.get_all_records())
        # تنظيف
        all_data['Mabadara'] = all_data['Mabadara'].astype(str).str.strip()
        all_data['Activity'] = all_data['Activity'].astype(str).str.strip()
        if 'Admin_Comment' not in all_data.columns: all_data['Admin_Comment'] = ""
        if 'Owner_Comment' not in all_data.columns: all_data['Owner_Comment'] = ""

        my_data = all_data[all_data['Mabadara'].isin(my_list)].copy()

        st.markdown("### 📌 تحديث أنشطة المبادرات")
        if not my_list:
            st.warning("⚠️ لا توجد مبادرات مسندة إليك.")
        else:
            sel_init = st.selectbox("اختر المبادرة", my_data['Mabadara'].unique())
            
            # إضافة نشاط
            with st.expander("➕ إضافة نشاط جديد لهذه المبادرة"):
                with st.form("add_activity_form"):
                    new_act_name = st.text_input("اسم النشاط الجديد")
                    c_new1, c_new2 = st.columns(2)
                    with c_new1: new_act_start = st.date_input("البداية", key="new_start")
                    with c_new2: new_act_end = st.date_input("النهاية", key="new_end")
                    if st.form_submit_button("إضافة النشاط"):
                        if new_act_name.strip() == "":
                            st.error("الرجاء كتابة اسم النشاط")
                        else:
                            try:
                                new_row = [sel_init, new_act_name, str(new_act_start), str(new_act_end), 0, "", "", ""]
                                ws_acts.append_row(new_row)
                                st.success("تمت الإضافة!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e: st.error(f"خطأ: {e}")

            acts_in_init = my_data[my_data['Mabadara'] == sel_init]
            if not acts_in_init.empty:
                st.markdown('<p class="step-header">اختر النشاط للتحديث</p>', unsafe_allow_html=True)
                sel_act_name = st.selectbox("النشاط", acts_in_init['Activity'].unique(), label_visibility="collapsed")

                if sel_act_name:
                    row = acts_in_init[acts_in_init['Activity'] == sel_act_name].iloc[0]
                    
                    # عرض ملاحظات المدير إن وجدت
                    if str(row.get('Admin_Comment', '')).strip():
                        st.markdown(f"<div class='admin-alert-box'>📢 <strong>ملاحظة من المدير:</strong> {row['Admin_Comment']}</div>", unsafe_allow_html=True)

                    with st.form("update_form"):
                        st.markdown("#### 📝 بيانات النشاط")
                        col_start, col_end, col_prog = st.columns(3)
                        with col_start:
                             new_start = st.date_input("تاريخ البداية", value=parse_date(row['Start_Date']))
                        with col_end:
                             new_end = st.date_input("تاريخ النهاية", value=parse_date(row['End_Date']))
                        with col_prog:
                             curr_prog = safe_int(row['Progress'])
                             new_prog = st.number_input("نسبة الإنجاز %", min_value=0, max_value=100, value=curr_prog, step=1)

                        st.markdown("#### 📎 المرفقات والملاحظات")
                        ext_link = st.text_input("رابط الدليل (URL)", value=str(row['Evidence_Link']))
                        
                        # --- نظام الملاحظات الجديد (مع التاريخ) ---
                        st.markdown("📜 **سجل الملاحظات السابق:**")
                        prev_notes = str(row['Owner_Comment'])
                        if prev_notes:
                            st.markdown(f"<div class='history-box'>{prev_notes}</div>", unsafe_allow_html=True)
                        else:
                            st.caption("لا توجد ملاحظات سابقة.")

                        new_note = st.text_area("✍️ إضافة ملاحظة جديدة (سيتم حفظها مع التاريخ والوقت تلقائياً)", height=100)
                        # ----------------------------------------------
                        
                        if st.form_submit_button("💾 حفظ التحديث"):
                            try:
                                sh_fresh = get_sheet_connection()
                                ws_fresh = sh_fresh.worksheet("Activities")
                                df_fresh = pd.DataFrame(ws_fresh.get_all_records())
                                df_fresh['Mabadara'] = df_fresh['Mabadara'].astype(str).str.strip()
                                df_fresh['Activity'] = df_fresh['Activity'].astype(str).str.strip()
                                mask = (df_fresh['Mabadara'] == sel_init) & (df_fresh['Activity'] == sel_act_name)
                                
                                if mask.any():
                                    # دمج الملاحظة الجديدة مع القديمة
                                    final_comment = append_timestamped_comment(prev_notes, new_note)
                                    
                                    df_fresh.loc[mask, 'Progress'] = int(new_prog)
                                    df_fresh.loc[mask, 'Start_Date'] = str(new_start)
                                    df_fresh.loc[mask, 'End_Date'] = str(new_end)
                                    df_fresh.loc[mask, 'Evidence_Link'] = str(ext_link)
                                    df_fresh.loc[mask, 'Owner_Comment'] = final_comment # حفظ الملاحظة المدمجة
                                    
                                    clean_data = clean_df_for_gspread(df_fresh)
                                    ws_fresh.update(values=[clean_data.columns.values.tolist()] + clean_data.values.tolist(), range_name='A1')
                                    st.success("✅ تم الحفظ وتحديث سجل الملاحظات!")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e: st.error(f"خطأ حفظ: {e}")
    except Exception as e:
        st.error(f"خطأ في بيانات الأنشطة: {e}")

    st.markdown("---")

    # --- الجزء 2: تحديث المؤشرات (تم تحويله إلى نظام النماذج Form لدعم التاريخ) ---
    st.markdown("### 📈 تحديث مؤشرات الأداء المسندة لي")
    try:
        ws_kpi = sh.worksheet("KPIs")
        df_kpi = pd.DataFrame(ws_kpi.get_all_records())
        
        if 'Owner' not in df_kpi.columns:
            st.warning("⚠️ عمود 'Owner' مفقود في ملف المؤشرات.")
        else:
            # التأكد من وجود عمود Owner_Comment
            if 'Owner_Comment' not in df_kpi.columns:
                df_kpi['Owner_Comment'] = ""
                
            current_email = st.session_state['user_info'].get('username', '').strip()
            my_kpis = df_kpi[
                (df_kpi['Owner'].astype(str).str.strip() == current_email) | 
                (df_kpi['Owner'].astype(str).str.strip() == user_name.strip())
            ]
            
            if my_kpis.empty:
                st.info("لا توجد مؤشرات أداء مرتبطة بحسابك حالياً.")
            else:
                st.caption("قم باختيار المؤشر لتحديث قيمته وإضافة ملاحظاتك.")
                
                # اختيار المؤشر
                sel_kpi_name = st.selectbox("اختر المؤشر", my_kpis['KPI_Name'].unique())
                
                if sel_kpi_name:
                    kpi_row = my_kpis[my_kpis['KPI_Name'] == sel_kpi_name].iloc[0]
                    
                    # عرض تفاصيل المؤشر
                    k1, k2, k3 = st.columns(3)
                    k1.metric("المستهدف", kpi_row['Target'])
                    k2.metric("المتحقق الحالي", kpi_row['Actual'])
                    k3.metric("الوحدة", kpi_row.get('Unit', '-'))

                    # عرض ملاحظات المدير
                    if str(kpi_row.get('Admin_Comment', '')).strip():
                        st.warning(f"📩 **ملاحظات المدير:** {kpi_row['Admin_Comment']}")

                    with st.form("update_kpi_form"):
                        st.write("#### 📝 تحديث البيانات")
                        
                        curr_actual = safe_float(kpi_row['Actual'])
                        new_actual = st.number_input("القيمة المتحققة (Actual)", value=curr_actual)
                        
                        # --- نظام ملاحظات المالك للمؤشر (مع التاريخ) ---
                        st.write("💬 **ملاحظاتك على المؤشر:**")
                        prev_kpi_notes = str(kpi_row.get('Owner_Comment', ''))
                        if prev_kpi_notes:
                            st.markdown(f"<div class='history-box'>{prev_kpi_notes}</div>", unsafe_allow_html=True)
                        
                        new_kpi_note = st.text_area("أضف ملاحظة جديدة للمدير (مع التاريخ التلقائي):")
                        # -----------------------------------------------------

                        if st.form_submit_button("💾 حفظ تحديث المؤشر"):
                            try:
                                # إعادة تحميل البيانات لضمان الحداثة
                                sh_fresh_kpi = get_sheet_connection()
                                ws_fresh_kpi = sh_fresh_kpi.worksheet("KPIs")
                                df_fresh_kpi = pd.DataFrame(ws_fresh_kpi.get_all_records())
                                
                                # التأكد من العمود مرة أخرى في النسخة الحديثة
                                if 'Owner_Comment' not in df_fresh_kpi.columns:
                                    df_fresh_kpi['Owner_Comment'] = ""

                                mask = df_fresh_kpi['KPI_Name'] == sel_kpi_name
                                
                                if mask.any():
                                    # دمج الملاحظات
                                    final_kpi_comment = append_timestamped_comment(prev_kpi_notes, new_kpi_note)
                                    
                                    df_fresh_kpi.loc[mask, 'Actual'] = new_actual
                                    df_fresh_kpi.loc[mask, 'Owner_Comment'] = final_kpi_comment
                                    
                                    clean_data = clean_df_for_gspread(df_fresh_kpi)
                                    ws_fresh_kpi.update(values=[clean_data.columns.values.tolist()] + clean_data.values.tolist(), range_name='A1')
                                    st.success("✅ تم تحديث المؤشر والملاحظات!")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"خطأ أثناء الحفظ: {e}")

    except Exception as e:
        st.error(f"خطأ في بيانات المؤشرات: {e}")

# ================================
# واجهة المشاهد (Viewer)
# ================================
def viewer_view(sh, user_name):
    st.markdown(f"### 👋 مرحباً، {user_name} (نسخة للاطلاع - المؤشرات فقط)")
    try:
        ws_kpi = sh.worksheet("KPIs")
        df_kpi = pd.DataFrame(ws_kpi.get_all_records())
        if df_kpi.empty:
            st.info("⚠️ لا توجد مؤشرات مسجلة في النظام.")
            return
        df_kpi['Target'] = df_kpi['Target'].apply(safe_float)
        df_kpi['Actual'] = df_kpi['Actual'].apply(safe_float)
        st.markdown("### 📊 الرسم البياني للمؤشرات")
        draw_kpi_chart(df_kpi)
    except Exception as e:
        st.error(f"خطأ في تحميل بيانات المؤشرات: {e}")

# ---------------------------------------------------------
# 5. التشغيل
# ---------------------------------------------------------
if not st.session_state['logged_in']:
    login()
else:
    with st.container():
        col_info, col_space, col_logout = st.columns([3, 5, 1])
        with col_info:
            user_name = st.session_state['user_info']['name']
            user_role = st.session_state['user_info']['role']
            st.markdown(f"### 👤 {user_name}")
            st.caption(f"الدور: {user_role}")
        with col_logout:
            st.write("") 
            if st.button("تسجيل الخروج", use_container_width=True):
                st.session_state['logged_in'] = False
                st.rerun()
    st.write("---") 

    try:
        connection = get_sheet_connection()
        role = str(st.session_state['user_info']['role']).strip().title()
        
        if role == 'Admin':
            st.title(f"لوحة القيادة التنفيذية")
            admin_view(connection, user_name)
        elif role == 'Owner':
            owner_view(connection, user_name, st.session_state['user_info']['assigned_initiative'])
        elif role == 'Viewer' or role == 'Staff': 
            viewer_view(connection, user_name)
        else:
            st.error(f"⚠️ خطأ: الدور '{role}' غير معروف.")
            
    except Exception as e:
        st.error(f"خطأ غير متوقع: {e}")

# --- Footer ---
st.markdown("""
<div class="footer">
    System Version: 20.0 (KPI Notes + Auto Timestamping)
</div>
""", unsafe_allow_html=True)
