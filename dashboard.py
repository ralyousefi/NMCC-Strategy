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
# 1. إعدادات الصفحة
# ---------------------------------------------------------
st.set_page_config(page_title="نظام إدارة الاستراتيجية", layout="wide", page_icon="📈")

st.markdown("""
<style>
    .main {direction: rtl;}
    h1, h2, h3, h4, p, div, input, select, textarea, .stSelectbox, .stNumberInput {text-align: right;}
    .stDataFrame {direction: rtl;}
    
    .activity-box {
        background-color: #f0f8ff;
        padding: 20px;
        border-radius: 10px;
        border-right: 6px solid #0068c9;
        margin: 20px 0;
        font-size: 18px;
        line-height: 1.8;
        color: #0e1117;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
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
        color: #555;
        font-size: 14px;
        margin-bottom: 5px;
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
# 2. إعدادات الاتصال (تم التعديل لتعمل أونلاين ومحلياً)
# ---------------------------------------------------------
SHEET_ID = "11tKfYa-Sqa96wDwQvMvChgRWaxgMRAWAIvul7p27ayY"

def get_creds():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # 1. المحاولة الأولى: القراءة من Streamlit Secrets (للموقع أونلاين)
    # نستخدم try-except لتجنب الأخطاء إذا لم تكن الأسرار موجودة
    try:
        if st.secrets is not None and 'gcp_service_account' in st.secrets:
            # تحويل الأسرار إلى قاموس بايثون
            creds_dict = dict(st.secrets["gcp_service_account"])
            
            # إصلاح مشكلة المسافات في المفتاح الخاص (Private Key Fix)
            # هذه أهم خطوة لكي يعمل المفتاح أونلاين
            if 'private_key' in creds_dict:
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')

            return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception:
        pass # إذا فشلت قراءة الأسرار، انتقل للمحاولة الثانية بصمت

    # 2. المحاولة الثانية: القراءة من ملف محلي (للعمل داخل Codespace)
    json_key_file = "credentials.json"
    if os.path.exists(json_key_file):
        return ServiceAccountCredentials.from_json_keyfile_name(json_key_file, scope)
        
    # 3. إذا فشلت المحاولتان
    st.error("""
    ⚠️ **خطأ في الاتصال!**
    لم يتم العثور على بيانات الاعتماد.
    - إذا كنت على الموقع: تأكد من إعداد Secrets في لوحة التحكم.
    - إذا كنت في Codespace: تأكد من وجود ملف credentials.json.
    """)
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
        st.markdown("### 🔐 تسجيل الدخول")
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("دخول", use_container_width=True):
            try:
                sh = get_sheet_connection()
                users_df = pd.DataFrame(sh.worksheet("Users").get_all_records())
                users_df['username'] = users_df['username'].astype(str).str.strip()
                # تنظيف البيانات
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
    st.title(f"لوحة القيادة التنفيذية - {user_name} 🌟")
    tab1, tab2 = st.tabs(["📋 متابعة المبادرات", "📊 مؤشرات الأداء (KPIs)"])
    
    # 1. متابعة المبادرات
    with tab1:
        try:
            ws_acts = sh.worksheet("Activities")
            df_acts = pd.DataFrame(ws_acts.get_all_records())
            
            if 'Admin_Comment' not in df_acts.columns:
                df_acts['Admin_Comment'] = ""

            if not df_acts.empty:
                st.markdown("### 🔎 مراجعة وتحديث المبادرات")
                init = st.selectbox("اختر المبادرة:", df_acts['Mabadara'].unique())
                filt = df_acts[df_acts['Mabadara'] == init]
                
                edited_acts = st.data_editor(
                    filt,
                    column_config={
                        "Evidence_Link": st.column_config.LinkColumn("رابط الدليل", display_text="📎 فتح الرابط"),
                        "Progress": st.column_config.ProgressColumn("الإنجاز %", format="%d%%", min_value=0, max_value=100),
                        "Admin_Comment": st.column_config.TextColumn("ملاحظات المدير (للموظف)", width="medium"),
                        "Owner_Comment": st.column_config.TextColumn("رد الموظف", disabled=True)
                    },
                    disabled=["Mabadara", "Activity", "Start_Date", "End_Date", "Progress", "Evidence_Link", "Owner_Comment"],
                    use_container_width=True,
                    key="admin_editor",
                    num_rows="fixed"
                )
                
                if st.button("💾 حفظ الملاحظات"):
                    with st.spinner("جاري حفظ الملاحظات..."):
                        try:
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

    # 2. المؤشرات
    with tab2:
        try:
            ws_kpi = sh.worksheet("KPIs")
            df_kpi = pd.DataFrame(ws_kpi.get_all_records())
            df_kpi['Target'] = df_kpi['Target'].apply(safe_float)
            df_kpi['Actual'] = df_kpi['Actual'].apply(safe_float)
            
            st.markdown("### ✏️ تحديث المؤشرات")
            with st.expander("فتح الجدول للتعديل"):
                edited_kpi = st.data_editor(df_kpi, num_rows="dynamic", use_container_width=True, key="kpi_editor")
                if st.button("حفظ المؤشرات"):
                    clean_data = clean_df_for_gspread(edited_kpi)
                    ws_kpi.update(values=[clean_data.columns.values.tolist()] + clean_data.values.tolist(), range_name='A1')
                    st.success("تم الحفظ!")
                    time.sleep(1)
                    st.rerun()
            
            # --- رسم بياني (Bar with Target Line) ---
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

# --- واجهة المالك ---
def owner_view(sh, user_name, my_initiatives_str):
    st.title(f"مرحباً، {user_name} 👷")
    
    if my_initiatives_str:
        my_list = [x.strip() for x in str(my_initiatives_str).split(',') if x.strip() != '']
    else:
        my_list = []

    if not my_list:
        st.warning("⚠️ لا توجد مبادرات مسندة.")
        return

    try:
        ws_acts = sh.worksheet("Activities")
        all_data = pd.DataFrame(ws_acts.get_all_records())
        all_data['Mabadara'] = all_data['Mabadara'].astype(str).str.strip()
        all_data['Activity'] = all_data['Activity'].astype(str).str.strip()
        
        if 'Admin_Comment' not in all_data.columns:
            all_data['Admin_Comment'] = ""

        my_data = all_data[all_data['Mabadara'].isin(my_list)].copy()

        # 1. اختيار المبادرة
        st.markdown('<p class="step-header">1️⃣ اختر المبادرة</p>', unsafe_allow_html=True)
        sel_init = st.selectbox("المبادرة", my_data['Mabadara'].unique(), label_visibility="collapsed")
        
        # إضافة نشاط
        with st.expander("➕ إضافة نشاط جديد لهذه المبادرة"):
            with st.form("add_activity_form"):
                st.info("سيتم إضافة النشاط مباشرة إلى قاعدة البيانات")
                new_act_name = st.text_input("اسم النشاط الجديد")
                c_new1, c_new2 = st.columns(2)
                with c_new1: new_act_start = st.date_input("البداية", key="new_start")
                with c_new2: new_act_end = st.date_input("النهاية", key="new_end")
                
                if st.form_submit_button("إضافة النشاط"):
                    if new_act_name.strip() == "":
                        st.error("اكتب اسم النشاط")
                    else:
                        with st.spinner("جاري الإضافة..."):
                            try:
                                new_row = [sel_init, new_act_name, str(new_act_start), str(new_act_end), 0, "", "", ""]
                                ws_acts.append_row(new_row)
                                st.success("تمت الإضافة!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"خطأ: {e}")

        st.markdown("---")

        # 2. اختيار النشاط
        acts_in_init = my_data[my_data['Mabadara'] == sel_init]
        if acts_in_init.empty:
            st.info("لا توجد أنشطة.")
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

                # عرض تعليق المدير
                admin_msg = str(row.get('Admin_Comment', '')).strip()
                if admin_msg:
                    st.markdown(f"""
                    <div class="admin-alert-box">
                        📢 <strong>تنبيه من الإدارة:</strong><br>{admin_msg}
                    </div>
                    """, unsafe_allow_html=True)

                # فورم التحديث
                with st.form("update_form"):
                    st.markdown("#### 📝 تحديث البيانات")
                    c1, c2 = st.columns(2)
                    with c1:
                        curr_prog = safe_int(row['Progress'])
                        new_prog = st.slider("نسبة الإنجاز %", 0, 100, curr_prog)
                    with c2:
                        new_start = st.date_input("البداية", value=parse_date(row['Start_Date']))
                        new_end = st.date_input("النهاية", value=parse_date(row['End_Date']))
                    
                    st.markdown("#### 📎 الروابط والملاحظات")
                    st.caption("تم تعطيل رفع الملفات مؤقتاً.")
                    ext_link = st.text_input("رابط الدليل (URL)", value=str(row['Evidence_Link']))
                    owner_cmt = st.text_area("ردك للإدارة", value=str(row['Owner_Comment']))
                    
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
                                    st.error("لم يتم العثور على النشاط.")
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
    with st.sidebar:
        st.write(f"👤 {st.session_state['user_info']['name']}")
        if st.button("تسجيل الخروج"):
            st.session_state['logged_in'] = False
            st.rerun()
            
    try:
        connection = get_sheet_connection()
        # تنظيف الدور من المسافات والأحرف الكبيرة/الصغيرة لضمان التطابق
        role = str(st.session_state['user_info']['role']).strip().title()
        
        if role == 'Admin':
            admin_view(connection, st.session_state['user_info']['name'])
        elif role == 'Owner':
            owner_view(connection, st.session_state['user_info']['name'], st.session_state['user_info']['assigned_initiative'])
        else:
            st.error(f"⚠️ خطأ في الصلاحيات: الدور '{role}' غير معروف في النظام. يرجى مراجعة المسؤول.")
            
    except Exception as e:
        st.error(f"خطأ غير متوقع: {e}")

# --- Footer: Version Number ---
st.markdown("""
<div class="footer">
    System Version: 14.2 (Hybrid: Online & Local)
</div>
""", unsafe_allow_html=True)
