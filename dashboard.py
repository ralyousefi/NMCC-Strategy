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
    "QI4SD": [
        "QI4SD - Metrology",
        "CMC",
        "B of CMC",
        "ILC",
        "CC",
        "OIML project groups",
        "OIML-CS - number of services offered"
    ],
    "البحث والتطوير": [
        "عدد الابحاث العلمية المنشورة في مجلات مصنفة دولياً Q1, Q2",
        "عدد المشاركات العلمية الدولية",
        "عدد الطلاب الملتحقين",
        "عدد فعاليات الاستقطاب الجامعي",
        "عدد المشاريع الوطنية",
        "عدد المشاركين سنوياً في برامج التبادل الفني"
    ],
    "الكفاءة التشغيلية": [
        "نسبة نضج الحوكمة المؤسسية KAQA",
        "مؤشر التميز المؤسسي",
        "نسبة الإجراءات المؤتمتة",
        "مستوى رضا المستفيدين",
        "التحول الرقمي DGA",
        "نسبة الدوران الوظيفي",
        "نسبة الإيرادات الى إجمالي ميزانية",
        "نسبة النمو في إيرادات"
    ]
}

def get_kpi_category(kpi_name):
    kpi_name = str(kpi_name).strip()
    for group, items in KPI_GROUPS.items():
        clean_items = [str(i).strip() for i in items]
        if kpi_name in clean_items:
            return group
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

def append_timestamped_comment(original_text, new_comment):
    if not new_comment or str(new_comment).strip() == "":
        return original_text
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = f"📅 {timestamp}: {str(new_comment).strip()}"
    
    if original_text and str(original_text).strip() != "":
        return f"{str(original_text)}\n----------------\n{new_entry}"
    else:
        return new_entry

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
# 5. واجهات المستخدمين
# ---------------------------------------------------------

# --- دالة رسم Bar Chart ---
def plot_group_barchart(df, group_title):
    if df.empty:
        st.info(f"لا توجد مؤشرات في مجموعة: {group_title}")
        return

    def get_color(row):
        target, actual = row['Target'], row['Actual']
        direction = str(row.get('Direction', 'تصاعدي')).strip()
        
        if direction == 'تنازلي':
            if actual <= target: return "#2ca02c"
            else: return "#d62728"
        else:
            if actual >= target:
                if actual > target: return "#1f77b4"
                return "#2ca02c"
            else: return "#d62728"

    df['Color'] = df.apply(get_color, axis=1)

    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df['KPI_Name'], 
        y=df['Actual'], 
        name='الفعلي', 
        marker_color=df['Color'], 
        text=df['Actual'],       
        textposition='auto',
        width=0.6
    ))
    
    fig.add_trace(go.Scatter(
        x=df['KPI_Name'], 
        y=df['Target'], 
        mode='markers',                  
        name='المستهدف', 
        marker=dict(symbol='line-ew', size=40, color='black', line=dict(width=3)), 
    ))

    fig.update_layout(
        title=dict(text=f"📊 {group_title}<br><span style='font-size:10px; color:transparent'>.</span>", x=0.5, xanchor='center'),
        barmode='overlay',                
        bargap=0.4,
        yaxis=dict(showgrid=True, gridcolor='lightgrey'),
        margin=dict(t=100, b=50, l=20, r=20),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center')
    )
    
    st.plotly_chart(fig, use_container_width=True)

# --- دالة العرض المنظم (Layout) ---
def display_kpi_layout(df_all):
    df_all['Category'] = df_all['KPI_Name'].apply(get_kpi_category)
    
    g1 = df_all[df_all['Category'] == "QI4SD"]
    g2 = df_all[df_all['Category'] == "البحث والتطوير"]
    g3 = df_all[df_all['Category'] == "الكفاءة التشغيلية"]
    
    col1, col2 = st.columns(2)
    with col1:
        plot_group_barchart(g1, "مجموعة QI4SD")
    with col2:
        plot_group_barchart(g2, "مجموعة البحث والتطوير")
        
    st.markdown("---")
    plot_group_barchart(g3, "مجموعة الكفاءة التشغيلية")

# ================================
# واجهة المدير (Admin)
# ================================
def admin_view(sh, user_name):
    st.markdown("### 📊 لوحة القيادة التنفيذية")
    
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

    tab1, tab2 = st.tabs(["📋 تفاصيل المبادرات", "📊 مؤشرات الأداء (المجموعات)"])
    
    # --- تبويب المبادرات ---
    with tab1:
        try:
            if 'Admin_Comment' not in df_acts.columns: df_acts['Admin_Comment'] = ""
            if not df_acts.empty:
                st.markdown("#### 🔎 مراجعة وتحديث المبادرات")
                st.caption("لإضافة ملاحظة: اكتب الملاحظة الجديدة في عمود '✍️ ملاحظة إدارية جديدة' ثم اضغط حفظ.")
                
                init = st.selectbox("اختر المبادرة:", df_acts['Mabadara'].unique())
                
                df_filt = df_acts[df_acts['Mabadara'] == init].copy()
                df_filt['New_Admin_Note'] = "" 
                
                edited_df = st.data_editor(
                    df_filt,
                    column_config={
                        "Activity": st.column_config.TextColumn("النشاط", width="large"),
                        "Progress": st.column_config.ProgressColumn("الإنجاز %", format="%d%%", min_value=0, max_value=100),
                        "Start_Date": st.column_config.DateColumn("تاريخ البداية", format="YYYY-MM-DD"),
                        "End_Date": st.column_config.DateColumn("تاريخ النهاية", format="YYYY-MM-DD"),
                        "Owner_Comment": st.column_config.TextColumn("آخر رد للموظف", width="medium"),
                        "Admin_Comment": st.column_config.TextColumn("سجل الملاحظات (للاطلاع)", width="medium"),
                        "New_Admin_Note": st.column_config.TextColumn("✍️ ملاحظة إدارية جديدة (اكتب هنا)", width="large"),
                        "Evidence_Link": st.column_config.LinkColumn("رابط الدليل", display_text="📎 فتح"),
                        "End_Date_DT": None, "Mabadara": None 
                    },
                    disabled=["Activity", "Progress", "Owner_Comment", "Admin_Comment", "Mabadara", "Start_Date", "End_Date"],
                    hide_index=True,
                    use_container_width=True,
                    key="admin_acts_editor",
                    num_rows="fixed"
                )
                
                if st.button("💾 حفظ الملاحظات الجديدة (أنشطة)"):
                    with st.spinner("جاري حفظ ودمج الملاحظات..."):
                        has_changes = False
                        if 'End_Date_DT' in df_acts.columns: df_acts = df_acts.drop(columns=['End_Date_DT'])
                        
                        for index, row in edited_df.iterrows():
                            new_note = str(row['New_Admin_Note']).strip()
                            if new_note:
                                has_changes = True
                                mask = (df_acts['Mabadara'] == row['Mabadara']) & (df_acts['Activity'] == row['Activity'])
                                if mask.any():
                                    old_note = df_acts.loc[mask, 'Admin_Comment'].values[0]
                                    final_note = append_timestamped_comment(old_note, new_note)
                                    df_acts.loc[mask, 'Admin_Comment'] = final_note
                        
                        if has_changes:
                            clean_data = clean_df_for_gspread(df_acts)
                            ws_acts.update(values=[clean_data.columns.values.tolist()] + clean_data.values.tolist(), range_name='A1')
                            st.success("✅ تم الحفظ! أضيفت الملاحظات الجديدة للسجل.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.info("لم يتم كتابة أي ملاحظات جديدة للحفظ.")

                st.markdown("---")
                st.markdown("##### 📜 عرض السجل التاريخي الكامل")
                act_for_history = st.selectbox("اختر النشاط لعرض سجله:", df_filt['Activity'].unique(), key="hist_act_sel")
                
                if act_for_history:
                    row_hist = df_filt[df_filt['Activity'] == act_for_history].iloc[0]
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("<div class='history-title'>تعليقات الموظف:</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='history-box'>{row_hist.get('Owner_Comment', 'لا يوجد')}</div>", unsafe_allow_html=True)
                    with c2:
                        st.markdown("<div class='history-title'>سجل ملاحظات المدير:</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='history-box'>{row_hist.get('Admin_Comment', 'لا يوجد')}</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"خطأ تحميل: {e}")

    # --- تبويب المؤشرات (Layout Mode) ---
    with tab2:
        try:
            ws_kpi = sh.worksheet("KPIs")
            df_kpi = pd.DataFrame(ws_kpi.get_all_records())
            
            for col in ['Admin_Comment', 'Owner_Comment', 'Owner']:
                if col not in df_kpi.columns: df_kpi[col] = ""
            
            df_kpi['Target'] = df_kpi['Target'].apply(safe_float)
            df_kpi['Actual'] = df_kpi['Actual'].apply(safe_float)
            
            # 1. عرض المخطط بالتنسيق الجديد
            display_kpi_layout(df_kpi)

            st.markdown("---")
            st.markdown("#### ✏️ تحديث البيانات والملاحظات")
            
            filter_cat = st.selectbox("📂 فلترة التعديل حسب المجموعة:", ["الكل"] + list(KPI_GROUPS.keys()))
            
            df_kpi['Category'] = df_kpi['KPI_Name'].apply(get_kpi_category)
            
            if filter_cat != "الكل":
                df_for_edit = df_kpi[df_kpi['Category'] == filter_cat].copy()
            else:
                df_for_edit = df_kpi.copy()

            df_for_edit['New_Admin_Note'] = ""
            
            edited_kpi = st.data_editor(
                df_for_edit, 
                num_rows="fixed", 
                use_container_width=True, 
                key="kpi_editor_admin",
                column_config={
                     "KPI_Name": st.column_config.TextColumn("المؤشر", width="large"),
                     "Target": st.column_config.NumberColumn("المستهدف", required=True), 
                     "Actual": st.column_config.NumberColumn("الفعلي"), 
                     "Owner": st.column_config.TextColumn("المسؤول"),
                     "Owner_Comment": st.column_config.TextColumn("ملاحظات المالك", width="medium"),
                     "Admin_Comment": st.column_config.TextColumn("سجل المدير", width="medium"),
                     "New_Admin_Note": st.column_config.TextColumn("✍️ ملاحظة جديدة", width="large"),
                     "Category": None, "Unit": None, "Direction": None, "Frequency": None 
                },
                disabled=["KPI_Name", "Actual", "Owner", "Owner_Comment", "Admin_Comment", "Category"]
            )
            
            if st.button("💾 حفظ تحديثات المؤشرات"):
                with st.spinner("جاري الحفظ..."):
                    has_changes = False
                    for index, row in edited_kpi.iterrows():
                        mask = df_kpi['KPI_Name'] == row['KPI_Name']
                        if mask.any():
                            if float(row['Target']) != float(df_kpi.loc[mask, 'Target'].values[0]):
                                df_kpi.loc[mask, 'Target'] = row['Target']
                                has_changes = True
                            
                            new_note = str(row['New_Admin_Note']).strip()
                            if new_note:
                                old_note = df_kpi.loc[mask, 'Admin_Comment'].values[0]
                                final_note = append_timestamped_comment(old_note, new_note)
                                df_kpi.loc[mask, 'Admin_Comment'] = final_note
                                has_changes = True

                    if has_changes:
                        clean_data = clean_df_for_gspread(df_kpi)
                        ws_kpi.update(values=[clean_data.columns.values.tolist()] + clean_data.values.tolist(), range_name='A1')
                        st.success("✅ تم الحفظ بنجاح!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.info("لا توجد تغييرات للحفظ.")
            
            st.markdown("---")
            st.markdown("##### 📜 سجل المؤشر")
            kpi_for_history = st.selectbox("اختر المؤشر لعرض سجله:", df_kpi['KPI_Name'].unique(), key="hist_kpi_sel")
            
            if kpi_for_history:
                row_kpi = df_kpi[df_kpi['KPI_Name'] == kpi_for_history].iloc[0]
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("<div class='history-title'>سجل ملاحظات المالك:</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='history-box'>{row_kpi.get('Owner_Comment', 'لا يوجد')}</div>", unsafe_allow_html=True)
                with c2:
                    st.markdown("<div class='history-title'>سجل ملاحظات المدير الكامل:</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='history-box'>{row_kpi.get('Admin_Comment', 'لا يوجد')}</div>", unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"خطأ KPI: {e}")

# ================================
# واجهة المالك (Owner) - (تبويبات + تعديل/حذف)
# ================================
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
        st.error(f"خطأ في تحميل البيانات: {e}")
        return

    # --- التبويبات ---
    tab1, tab2, tab3 = st.tabs(["📋 تحديث الأنشطة", "✏️ تحديث مؤشراتي", "📊 كافة المؤشرات (للاطلاع)"])

    # 1. تبويب تحديث الأنشطة
    with tab1:
        st.markdown("### 📌 تحديث أنشطة المبادرات")
        if not my_list:
            st.warning("⚠️ لا توجد مبادرات مسندة إليك.")
        else:
            sel_init = st.selectbox("اختر المبادرة", my_data['Mabadara'].unique())
            
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
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e: st.error(f"خطأ: {e}")

            acts_in_init = my_data[my_data['Mabadara'] == sel_init]
            if not acts_in_init.empty:
                st.markdown('<p class="step-header">اختر النشاط للتحديث</p>', unsafe_allow_html=True)
                sel_act_name = st.selectbox("النشاط", acts_in_init['Activity'].unique(), label_visibility="collapsed")

                if sel_act_name:
                    row = acts_in_init[acts_in_init['Activity'] == sel_act_name].iloc[0]
                    
                    # --- إعادة تفعيل قسم الإعدادات (تعديل وحذف) ---
                    with st.expander("⚙️ إعدادات النشاط (تعديل الاسم / حذف)"):
                        st.info("تنبيه: هذه الإجراءات تؤثر على هيكل النشاط.")
                        c_edit, c_delete = st.columns(2)
                        
                        # 1. تعديل الاسم
                        with c_edit:
                            st.markdown("##### ✏️ تعديل مسمى النشاط")
                            new_name_val = st.text_input("الاسم الجديد", value=sel_act_name, key="rename_act")
                            if st.button("تحديث الاسم"):
                                if new_name_val.strip() != sel_act_name:
                                    try:
                                        cell = ws_acts.find(sel_act_name)
                                        if cell:
                                            ws_acts.update_cell(cell.row, cell.col, new_name_val)
                                            st.success("تم تعديل الاسم بنجاح!")
                                            time.sleep(1)
                                            st.rerun()
                                        else: st.error("لم يتم العثور على الخلية.")
                                    except Exception as e: st.error(f"حدث خطأ: {e}")
                                else: st.warning("الاسم الجديد مطابق للاسم الحالي.")

                        # 2. حذف النشاط
                        with c_delete:
                            st.markdown("##### 🗑️ حذف النشاط")
                            st.warning("سيتم حذف النشاط وسجله بالكامل.")
                            if st.button("تأكيد الحذف", type="primary"):
                                try:
                                    cell_del = ws_acts.find(sel_act_name)
                                    if cell_del:
                                        ws_acts.delete_rows(cell_del.row)
                                        st.success("تم حذف النشاط.")
                                        time.sleep(1)
                                        st.rerun()
                                    else: st.error("لم يتم العثور على النشاط.")
                                except Exception as e: st.error(f"خطأ في الحذف: {e}")
                    # -----------------------------------------------

                    if str(row.get('Admin_Comment', '')).strip():
                        st.markdown(f"<div class='admin-alert-box'>📢 <strong>ملاحظة من المدير:</strong><div class='history-box'>{row['Admin_Comment']}</div></div>", unsafe_allow_html=True)

                    with st.form("update_form"):
                        st.markdown("#### 📝 بيانات النشاط")
                        col_start, col_end, col_prog = st.columns(3)
                        with col_start: new_start = st.date_input("تاريخ البداية", value=parse_date(row['Start_Date']))
                        with col_end: new_end = st.date_input("تاريخ النهاية", value=parse_date(row['End_Date']))
                        with col_prog:
                             curr_prog = safe_int(row['Progress'])
                             new_prog = st.number_input("نسبة الإنجاز %", min_value=0, max_value=100, value=curr_prog, step=1)

                        st.markdown("#### 📎 المرفقات والملاحظات")
                        ext_link = st.text_input("رابط الدليل (URL)", value=str(row['Evidence_Link']))
                        
                        st.markdown("📜 **سجل الملاحظات السابق:**")
                        prev_notes = str(row['Owner_Comment'])
                        if prev_notes: st.markdown(f"<div class='history-box'>{prev_notes}</div>", unsafe_allow_html=True)
                        else: st.caption("لا توجد ملاحظات سابقة.")

                        new_note = st.text_area("✍️ إضافة ملاحظة جديدة (سيتم حفظها مع التاريخ والوقت تلقائياً)", height=100)
                        
                        if st.form_submit_button("💾 حفظ التحديث"):
                            try:
                                sh_fresh = get_sheet_connection()
                                ws_fresh = sh_fresh.worksheet("Activities")
                                df_fresh = pd.DataFrame(ws_fresh.get_all_records())
                                df_fresh['Mabadara'] = df_fresh['Mabadara'].astype(str).str.strip()
                                df_fresh['Activity'] = df_fresh['Activity'].astype(str).str.strip()
                                mask = (df_fresh['Mabadara'] == sel_init) & (df_fresh['Activity'] == sel_act_name)
                                
                                if mask.any():
                                    final_comment = append_timestamped_comment(prev_notes, new_note)
                                    df_fresh.loc[mask, 'Progress'] = int(new_prog)
                                    df_fresh.loc[mask, 'Start_Date'] = str(new_start)
                                    df_fresh.loc[mask, 'End_Date'] = str(new_end)
                                    df_fresh.loc[mask, 'Evidence_Link'] = str(ext_link)
                                    df_fresh.loc[mask, 'Owner_Comment'] = final_comment
                                    
                                    clean_data = clean_df_for_gspread(df_fresh)
                                    ws_fresh.update(values=[clean_data.columns.values.tolist()] + clean_data.values.tolist(), range_name='A1')
                                    st.success("✅ تم الحفظ وتحديث سجل الملاحظات!")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e: st.error(f"خطأ حفظ: {e}")

    # 2. تبويب تحديث مؤشراتي
    with tab2:
        st.markdown("### 📈 تحديث مؤشرات الأداء المسندة لي")
        current_email = st.session_state['user_info'].get('username', '').strip()
        my_kpis = df_kpi[
            (df_kpi['Owner'].astype(str).str.strip() == current_email) | 
            (df_kpi['Owner'].astype(str).str.strip() == user_name.strip())
        ]
        
        if my_kpis.empty:
            st.info("لا توجد مؤشرات أداء مرتبطة بحسابك حالياً.")
        else:
            st.caption("قم باختيار المؤشر لتحديث قيمته وإضافة ملاحظاتك.")
            sel_kpi_name = st.selectbox("اختر المؤشر", my_kpis['KPI_Name'].unique())
            
            if sel_kpi_name:
                kpi_row = my_kpis[my_kpis['KPI_Name'] == sel_kpi_name].iloc[0]
                k1, k2, k3 = st.columns(3)
                k1.metric("المستهدف", kpi_row['Target'])
                k2.metric("المتحقق الحالي", kpi_row['Actual'])
                k3.metric("الوحدة", kpi_row.get('Unit', '-'))

                if str(kpi_row.get('Admin_Comment', '')).strip():
                    st.markdown(f"<div class='admin-alert-box'>📢 <strong>ملاحظات المدير:</strong><div class='history-box'>{kpi_row['Admin_Comment']}</div></div>", unsafe_allow_html=True)

                with st.form("update_kpi_form"):
                    st.write("#### 📝 تحديث البيانات")
                    curr_actual = safe_float(kpi_row['Actual'])
                    new_actual = st.number_input("القيمة المتحققة (Actual)", value=curr_actual)
                    
                    st.write("💬 **سجل ملاحظاتك السابق:**")
                    prev_kpi_notes = str(kpi_row.get('Owner_Comment', ''))
                    if prev_kpi_notes: st.markdown(f"<div class='history-box'>{prev_kpi_notes}</div>", unsafe_allow_html=True)
                    
                    new_kpi_note = st.text_area("أضف ملاحظة جديدة للمدير (مع التاريخ التلقائي):")

                    if st.form_submit_button("💾 حفظ تحديث المؤشر"):
                        try:
                            sh_fresh_kpi = get_sheet_connection()
                            ws_fresh_kpi = sh_fresh_kpi.worksheet("KPIs")
                            df_fresh_kpi = pd.DataFrame(ws_fresh_kpi.get_all_records())
                            if 'Owner_Comment' not in df_fresh_kpi.columns:
                                df_fresh_kpi['Owner_Comment'] = ""
                            mask = df_fresh_kpi['KPI_Name'] == sel_kpi_name
                            if mask.any():
                                final_kpi_comment = append_timestamped_comment(prev_kpi_notes, new_kpi_note)
                                df_fresh_kpi.loc[mask, 'Actual'] = new_actual
                                df_fresh_kpi.loc[mask, 'Owner_Comment'] = final_kpi_comment
                                
                                clean_data = clean_df_for_gspread(df_fresh_kpi)
                                ws_fresh_kpi.update(values=[clean_data.columns.values.tolist()] + clean_data.values.tolist(), range_name='A1')
                                st.success("✅ تم تحديث المؤشر والملاحظات!")
                                time.sleep(1)
                                st.rerun()
                        except Exception as e: st.error(f"خطأ أثناء الحفظ: {e}")

    # 3. تبويب كافة المؤشرات
    with tab3:
        st.markdown("### 📊 لوحة المؤشرات العامة (للاطلاع)")
        st.caption("تعرض هذه اللوحة جميع مؤشرات أداء المركز للمتابعة العامة.")
        display_kpi_layout(df_kpi)

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
        
        display_kpi_layout(df_kpi)
        
    except Exception as e:
        st.error(f"خطأ في تحميل بيانات المؤشرات: {e}")

# ---------------------------------------------------------
# 5. التشغيل
# ---------------------------------------------------------
if not st.session_state['logged_in']:
    login()
else:
    with st.container():
        col_info, col_space, col_logout, col_logo = st.columns([3, 4, 1, 1])
        
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
                
        with col_logo:
             if os.path.exists("logo.png"):
                 st.image("logo.png", width=80)
             else:
                 pass

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
    System Version: 32.0 (NMCC - 2026)
</div>
""", unsafe_allow_html=True)
