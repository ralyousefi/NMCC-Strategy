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

# تحسينات CSS للهوية البصرية وبطاقات الأداء
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
    }
    
    h1, h2, h3, h4, p, div, input, select, textarea, .stSelectbox, .stNumberInput {text-align: right;}
    .stDataFrame {direction: rtl;}
    
    /* تنسيق بطاقات الأداء (KPI Cards) */
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

    /* تنسيق صندوق النشاط */
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
    
    /* تنسيق تنبيه الإدارة */
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
# 2. إعدادات الاتصال (الهجينة)
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

# --- واجهة الأدمن ---
def admin_view(sh, user_name):
    st.markdown("### 📊 نظرة عامة")
    
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
            if 'Admin_Comment' not in df_acts.columns:
                df_acts['Admin_Comment'] = ""

            if not df_acts.empty:
                st.markdown("#### 🔎 مراجعة وتحديث المبادرات")
                init = st.selectbox("اختر المبادرة:", df_acts['Mabadara'].unique())
                filt = df_acts[df_acts['Mabadara'] == init]
                
                edited_acts = st.data_editor(
                    filt,
                    column_config={
                        "Evidence_Link": st.column_config.LinkColumn("رابط الدليل", display_text="📎 فتح"),
                        "Progress": st.column_config.ProgressColumn("الإنجاز %", format="%d%%", min_value=0, max_value=100),
                        "Admin_Comment": st.column_config.TextColumn("ملاحظات المدير", width="medium"),
                        "Owner_Comment": st.column_config.TextColumn("رد الموظف", disabled=True),
                        "End_Date_DT": None 
                    },
                    disabled=["Mabadara", "Activity", "Start_Date", "End_Date", "Progress", "Evidence_Link", "Owner_Comment"],
                    use_container_width=True,
                    key="admin_editor",
                    num_rows="fixed"
                )
                
                if st.button("💾 حفظ الملاحظات"):
                    with st.spinner("جاري حفظ الملاحظات..."):
                        try:
                            if 'End_Date_DT' in df_acts.columns:
                                df_acts = df_acts.drop(columns=['End_Date_DT'])

                            for index, row in edited_acts.iterrows():
                                mask = (df_acts['Mabadara'] == row['Mabadara']) & (df_acts['Activity'] == row['Activity'])
                                df_acts.loc[mask, 'Admin_Comment'] = row['Admin_Comment']
                            
                            clean_data = clean_df_for_gspread(df_acts)
                            ws_acts.update(values=[clean_data.columns.values.tolist()] + clean_data.values.tolist(), range_name='A1')
                            
                            st.success("✅ تم حفظ الملاحظات بنجاح!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"حدث خطأ أثناء الحفظ: {e}")
        except Exception as e:
            st.error(f"خطأ تحميل: {e}")

    with tab2:
        try:
            ws_kpi = sh.worksheet("KPIs")
            df_kpi = pd.DataFrame(ws_kpi.get_all_records())
            df_kpi['Target'] = df_kpi['Target'].apply(safe_float)
            df_kpi['Actual'] = df_kpi['Actual'].apply(safe_float)
            
            st.markdown("#### ✏️ تحديث المؤشرات")
            with st.expander("فتح الجدول للتعديل"):
                edited_kpi = st.data_editor(df_kpi, num_rows="dynamic", use_container_width=True, key="kpi_editor")
                if st.button("حفظ المؤشرات"):
                    clean_data = clean_df_for_gspread(edited_kpi)
                    ws_kpi.update(values=[clean_data.columns.values.tolist()] + clean_data.values.tolist(), range_name='A1')
                    st.success("تم الحفظ!")
                    time.sleep(1)
                    st.rerun()
            
            if not edited_kpi.empty:
                def get_status(row):
                    target, actual = row['Target'], row['Actual']
                    direction = row.get('Direction', 'تصاعدي') 
                    if direction == 'تنازلي': 
                        return "متقدم (أزرق)" if actual < target else "متحقق (أخضر)" if actual == target else "متأخر (أحمر)"
                    else: 
                        return "متقدم (أزرق)" if actual > target else "متحقق (أخضر)" if actual == target else "متأخر (أحمر)"

                edited_kpi['Status'] = edited_kpi.apply(get_status, axis=1)
                
                fig = go.Figure()
                status_colors = edited_kpi['Status'].map({
                    "متقدم (أزرق)": "#1f77b4", 
                    "متحقق (أخضر)": "#2ca02c", 
                    "متأخر (أحمر)": "#d62728"
                }).fillna("grey")

                fig.add_trace(go.Bar(
                    x=edited_kpi['KPI_Name'], 
                    y=edited_kpi['Actual'], 
                    name='الفعلي', 
                    marker_color=status_colors,
                    text=edited_kpi['Actual'],       
                    textposition='inside',           
                    width=0.5                        
                ))
                
                fig.add_trace(go.Scatter(
                    x=edited_kpi['KPI_Name'], 
                    y=edited_kpi['Target'], 
                    mode='markers',                  
                    name='المستهدف', 
                    marker=dict(symbol='line-ew', size=50, color='black', line=dict(width=3)), 
                ))

                fig.update_layout(
                    title="مقارنة الأداء (الفعلي vs المستهدف)",
                    xaxis_title="المؤشر",
                    yaxis_title="القيمة",
                    barmode='overlay',                
                    bargap=0.4,                       
                    legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center'),
                    yaxis=dict(showgrid=True, gridcolor='lightgrey'),
                )
                st.plotly_chart(fig, use_container_width=True)
                
        except Exception as e:
            st.error(f"خطأ KPI: {e}")

# --- واجهة المالك (Owner View) ---
def owner_view(sh, user_name, my_initiatives_str):
    # لا حاجة لعنوان هنا لأنه موجود في الهيدر الرئيسي الآن، لكن يمكن تركه كترحيب
    # st.title(f"مرحباً، {user_name} 👋")
    
    if my_initiatives_str:
        my_list = [x.strip() for x in str(my_initiatives_str).split(',') if x.strip() != '']
    else:
        my_list = []

    if not my_list:
        st.warning("⚠️ لا توجد مبادرات مسندة إليك.")
        return

    try:
        ws_acts = sh.worksheet("Activities")
        all_data = pd.DataFrame(ws_acts.get_all_records())
        all_data['Mabadara'] = all_data['Mabadara'].astype(str).str.strip()
        all_data['Activity'] = all_data['Activity'].astype(str).str.strip()
        
        if 'Admin_Comment' not in all_data.columns:
            all_data['Admin_Comment'] = ""

        my_data = all_data[all_data['Mabadara'].isin(my_list)].copy()

        st.markdown('<p class="step-header">1️⃣ اختر المبادرة</p>', unsafe_allow_html=True)
        sel_init = st.selectbox("المبادرة", my_data['Mabadara'].unique(), label_visibility="collapsed")
        
        with st.expander("➕ إضافة نشاط جديد لهذه المبادرة"):
            with st.form("add_activity_form"):
                st.info("سيتم إضافة النشاط مباشرة إلى قاعدة البيانات")
                new_act_name = st.text_input("اسم النشاط الجديد")
                c_new1, c_new2 = st.columns(2)
                with c_new1: new_act_start = st.date_input("البداية", key="new_start")
                with c_new2: new_act_end = st.date_input("النهاية", key="new_end")
                
                if st.form_submit_button("إضافة النشاط"):
                    if new_act_name.strip() == "":
                        st.error("الرجاء كتابة اسم النشاط")
                    else:
                        with st.spinner("جاري الإضافة..."):
                            try:
                                new_row = [sel_init, new_act_name, str(new_act_start), str(new_act_end), 0, "", "", ""]
                                ws_acts.append_row(new_row)
                                st.success("تمت الإضافة بنجاح!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"خطأ: {e}")

        st.markdown("---")

        acts_in_init = my_data[my_data['Mabadara'] == sel_init]
        if acts_in_init.empty:
            st.info("لا توجد أنشطة لهذه المبادرة.")
        else:
            st.markdown('<p class="step-header">2️⃣ اختر النشاط للتحديث</p>', unsafe_allow_html=True)
            sel_act_name = st.selectbox("النشاط", acts_in_init['Activity'].unique(), label_visibility="collapsed")

            if sel_act_name:
                st.markdown(f"""
                <div class="activity-box">
                    <strong style="color:#0068c9;">📋 تفاصيل النشاط:</strong><br>{sel_act_name}
                </div>
                """, unsafe_allow_html=True)
                
                row = acts_in_init[acts_in_init['Activity'] == sel_act_name].iloc[0]

                admin_msg = str(row.get('Admin_Comment', '')).strip()
                if admin_msg:
                    st.markdown(f"""
                    <div class="admin-alert-box">
                        📢 <strong>تنبيه من الإدارة:</strong><br>{admin_msg}
                    </div>
                    """, unsafe_allow_html=True)

                with st.form("update_form"):
                    st.markdown("#### 📝 تحديث البيانات")
                    
                    # --- التعديل 2: إعادة هيكلة صندوق البيانات ---
                    # 1. التواريخ في الأعلى
                    # بسبب الاتجاه RTL: العمود الأول (يمين) للبداية، العمود الثاني (يسار) للنهاية
                    col_date_right, col_date_left = st.columns(2)
                    
                    with col_date_right:
                         new_start = st.date_input("البداية", value=parse_date(row['Start_Date']))
                    
                    with col_date_left:
                         new_end = st.date_input("النهاية", value=parse_date(row['End_Date']))
                    
                    # 2. نسبة الإنجاز تحتهم (بعرض كامل)
                    st.write("") # مسافة جمالية
                    curr_prog = safe_int(row['Progress'])
                    new_prog = st.slider("نسبة الإنجاز %", 0, 100, curr_prog)
                    # ---------------------------------------------
                    
                    st.markdown("#### 📎 الروابط والملاحظات")
                    st.caption("لإرفاق ملف، يرجى وضع رابط سحابي (Google Drive, OneDrive, Nextcloud).")
                    ext_link = st.text_input("رابط الدليل (URL)", value=str(row['Evidence_Link']))
                    owner_cmt = st.text_area("ردك للإدارة / ملاحظات", value=str(row['Owner_Comment']))
                    
                    if st.form_submit_button("💾 حفظ التحديث", use_container_width=True):
                        try:
                            with st.spinner("جاري الحفظ..."):
                                sh_fresh = get_sheet_connection()
                                ws_fresh = sh_fresh.worksheet("Activities")
                                df_fresh = pd.DataFrame(ws_fresh.get_all_records())
                                
                                df_fresh['Mabadara'] = df_fresh['Mabadara'].astype(str).str.strip()
                                df_fresh['Activity'] = df_fresh['Activity'].astype(str).str.strip()
                                
                                mask = (df_fresh['Mabadara'] == sel_init) & (df_fresh['Activity'] == sel_act_name)
                                
                                if mask.any():
                                    df_fresh.loc[mask, 'Progress'] = int(new_prog)
                                    df_fresh.loc[mask, 'Start_Date'] = str(new_start)
                                    df_fresh.loc[mask, 'End_Date'] = str(new_end)
                                    df_fresh.loc[mask, 'Evidence_Link'] = str(ext_link)
                                    df_fresh.loc[mask, 'Owner_Comment'] = str(owner_cmt)
                                    
                                    clean_data = clean_df_for_gspread(df_fresh)
                                    ws_fresh.update(values=[clean_data.columns.values.tolist()] + clean_data.values.tolist(), range_name='A1')
                                    st.success("✅ تم الحفظ!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("لم يتم العثور على النشاط في قاعدة البيانات.")
                        except Exception as e:
                            st.error(f"خطأ في الحفظ: {e}")
    except Exception as e:
        st.error(f"خطأ: {e}")

# ---------------------------------------------------------
# 5. التشغيل
# ---------------------------------------------------------
if not st.session_state['logged_in']:
    login()
else:
    # --- التعديل 1: حذف Sidebar ووضع الهيدر العلوي ---
    # إنشاء حاوية علوية للمعلومات وزر الخروج
    with st.container():
        # تقسيم الأعمدة:
        # col_info: يمين (معلومات المستخدم)
        # col_space: وسط (فراغ)
        # col_logout: يسار (زر الخروج)
        # ملاحظة: لأن الاتجاه RTL، فإن العمود الأول يظهر على اليمين.
        col_info, col_space, col_logout = st.columns([3, 5, 1])
        
        with col_info:
            user_name = st.session_state['user_info']['name']
            user_role = st.session_state['user_info']['role']
            st.markdown(f"### 👤 {user_name}")
            st.caption(f"الدور: {user_role}")
            
        with col_logout:
            st.write("") # محاذاة عمودية بسيطة
            if st.button("تسجيل الخروج", use_container_width=True):
                st.session_state['logged_in'] = False
                st.rerun()
    
    st.write("---") # خط فاصل
    # ---------------------------------------------------

    try:
        connection = get_sheet_connection()
        role = str(st.session_state['user_info']['role']).strip().title()
        
        if role == 'Admin':
            # نمرر اسم المستخدم للعنوان
            st.title(f"لوحة القيادة التنفيذية - {st.session_state['user_info']['name']}")
            admin_view(connection, st.session_state['user_info']['name'])
        elif role == 'Owner':
            owner_view(connection, st.session_state['user_info']['name'], st.session_state['user_info']['assigned_initiative'])
        else:
            st.error(f"⚠️ خطأ: الدور '{role}' غير معروف.")
            
    except Exception as e:
        st.error(f"خطأ غير متوقع: {e}")

# --- Footer ---
st.markdown("""
<div class="footer">
    System Version: 16.0 (Layout Updated)
</div>
""", unsafe_allow_html=True)

