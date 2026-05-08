"""
chat_module.py — واجهة محادثة بين المدير والموظف
الإصدار: 1.0

المبدأ:
  - التعليقات مخزّنة في عمودَي Owner_Comment و Admin_Comment الموجودَين
  - كل رسالة بصيغة: 📅 YYYY-MM-DD HH:MM [ROLE]: النص
  - يُعرض الحوار كفقاعات محادثة مرتّبة زمنياً
  - لا حاجة لعمود جديد في الشيت

الاستخدام في dashboard.py:
    from chat_module import show_activity_chat, show_kpi_chat
"""

import re
import streamlit as st
import pandas as pd
from datetime import datetime

# ──────────────────────────────────────────────
# CSS فقاعات المحادثة
# ──────────────────────────────────────────────
CHAT_CSS = """
<style>
.chat-wrap {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px 4px;
    direction: rtl;
}
.bubble {
    max-width: 78%;
    padding: 10px 14px;
    border-radius: 16px;
    font-size: 13.5px;
    line-height: 1.6;
    position: relative;
    word-break: break-word;
    font-family: 'Tajawal', sans-serif;
}
/* رسائل المدير — يمين */
.bubble-admin {
    background: #1a237e;
    color: #fff;
    align-self: flex-end;
    border-bottom-right-radius: 4px;
    margin-left: auto;
}
.bubble-admin .meta {
    font-size: 11px;
    opacity: .7;
    margin-bottom: 4px;
    text-align: right;
}
/* رسائل الموظف — يسار */
.bubble-owner {
    background: #f0f4ff;
    color: #1a237e;
    border: 1px solid #dce4ff;
    align-self: flex-start;
    border-bottom-left-radius: 4px;
    margin-right: auto;
}
.bubble-owner .meta {
    font-size: 11px;
    color: #5c6bc0;
    margin-bottom: 4px;
    text-align: right;
}
.chat-empty {
    text-align: center;
    color: #aaa;
    font-size: 13px;
    padding: 24px 0;
    direction: rtl;
}
.chat-divider {
    text-align: center;
    color: #bbb;
    font-size: 11px;
    padding: 4px 0;
    direction: rtl;
}
</style>
"""

# ──────────────────────────────────────────────
# تحليل النص إلى رسائل مرتّبة
# ──────────────────────────────────────────────
_MSG_PATTERN = re.compile(
    r"📅\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})"   # التاريخ
    r"(?:\s*\[(\w+)\])?"                           # [ROLE] اختياري
    r":\s*(.*?)(?=📅|\Z)",                         # النص
    re.DOTALL,
)


def _parse_messages(text: str, default_role: str) -> list[dict]:
    """
    يحوّل نص التعليقات إلى قائمة رسائل مرتّبة.
    كل رسالة: {"dt": datetime, "role": str, "text": str}
    """
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
        except ValueError:
            dt = datetime.min
        msgs.append({"dt": dt, "role": role, "text": body})
    return msgs


def _merge_and_sort(owner_text: str, admin_text: str) -> list[dict]:
    """يدمج تعليقات الطرفين ويرتّبها زمنياً."""
    msgs = (
        _parse_messages(owner_text, "Owner") +
        _parse_messages(admin_text,  "Admin")
    )
    return sorted(msgs, key=lambda x: x["dt"])


def _format_new_comment(text: str, role: str) -> str:
    """يبني نص الرسالة الجديدة بالصيغة المعتمدة مع وسم الدور."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"📅 {ts} [{role}]: {text.strip()}"


def _append_comment(original: str, new_entry: str) -> str:
    """يُلحق الرسالة الجديدة بالنص الأصلي."""
    original = str(original).strip()
    return f"{original}\n{new_entry}" if original else new_entry


# ──────────────────────────────────────────────
# عرض فقاعات المحادثة
# ──────────────────────────────────────────────
def _render_chat(messages: list[dict], current_role: str) -> None:
    """يعرض الرسائل كفقاعات محادثة."""
    st.markdown(CHAT_CSS, unsafe_allow_html=True)

    if not messages:
        st.markdown(
            "<div class='chat-empty'>💬 لا توجد رسائل بعد — ابدأ المحادثة أدناه</div>",
            unsafe_allow_html=True,
        )
        return

    html = "<div class='chat-wrap'>"
    prev_date = None

    for msg in messages:
        msg_date = msg["dt"].strftime("%Y-%m-%d")
        # فاصل تاريخ
        if msg_date != prev_date:
            label = msg["dt"].strftime("%A، %Y-%m-%d")
            html += f"<div class='chat-divider'>── {label} ──</div>"
            prev_date = msg_date

        role    = msg["role"]
        time_s  = msg["dt"].strftime("%H:%M")
        is_admin = (role == "Admin")
        cls      = "bubble-admin" if is_admin else "bubble-owner"
        sender   = "المدير" if is_admin else "الموظف"
        text_esc = msg["text"].replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

        html += f"""
        <div style='display:flex; justify-content:{"flex-end" if is_admin else "flex-start"}'>
          <div class='bubble {cls}'>
            <div class='meta'>{sender} · {time_s}</div>
            {text_esc}
          </div>
        </div>"""

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# الواجهة الرئيسية — نشاط
# ──────────────────────────────────────────────
def show_activity_chat(
    ws,                      # ورقة Activities (gspread worksheet)
    df_acts: pd.DataFrame,   # DataFrame الأنشطة المحمّل
    mabadara: str,           # اسم المبادرة
    activity: str,           # اسم النشاط
    current_role: str,       # "Admin" | "Owner"
    current_user: str,       # اسم المستخدم للعرض
) -> None:
    """
    يعرض واجهة المحادثة لنشاط محدد.

    مثال الاستخدام في admin_view / owner_view:
        from chat_module import show_activity_chat
        show_activity_chat(ws_acts, df_acts, sel_init, sel_act,
                           current_role="Admin", current_user=user_name)
    """
    mask = (
        (df_acts["Mabadara"].astype(str).str.strip() == mabadara.strip()) &
        (df_acts["Activity"].astype(str).str.strip() == activity.strip())
    )
    if not mask.any():
        st.warning("لم يُعثر على النشاط.")
        return

    row          = df_acts[mask].iloc[0]
    owner_text   = str(row.get("Owner_Comment", "")).strip()
    admin_text   = str(row.get("Admin_Comment", "")).strip()
    messages     = _merge_and_sort(owner_text, admin_text)

    # ── عنوان المحادثة ──
    short_act = activity[:55] + "…" if len(activity) > 55 else activity
    st.markdown(f"#### 💬 محادثة: {short_act}")
    st.caption(f"المبادرة: {mabadara[:60]}")

    # ── عداد الرسائل ──
    n_admin = sum(1 for m in messages if m["role"] == "Admin")
    n_owner = sum(1 for m in messages if m["role"] == "Owner")
    c1, c2, c3 = st.columns(3)
    c1.metric("📨 إجمالي الرسائل", len(messages))
    c2.metric("🔵 رسائل المدير",    n_admin)
    c3.metric("🟢 رسائل الموظف",   n_owner)
    st.markdown("---")

    # ── عرض المحادثة ──
    chat_height = min(max(len(messages) * 80, 200), 500)
    with st.container(height=chat_height):
        _render_chat(messages, current_role)

    # ── صندوق الرد ──
    st.markdown("---")
    sender_label = "المدير" if current_role == "Admin" else "الموظف"
    new_msg = st.text_area(
        f"✍️ رسالة جديدة ({sender_label})",
        placeholder="اكتب ردك هنا...",
        height=90,
        key=f"chat_input_{mabadara[:20]}_{activity[:20]}",
    )

    col_send, col_clear = st.columns([2, 1])
    with col_send:
        if st.button("📤 إرسال", type="primary",
                     use_container_width=True,
                     key=f"chat_send_{mabadara[:15]}_{activity[:15]}"):
            if not new_msg.strip():
                st.warning("الرسالة فارغة.")
            else:
                _send_activity_message(
                    ws, df_acts, mask,
                    new_msg, current_role,
                )
    with col_clear:
        st.caption(f"الوقت: {datetime.now().strftime('%H:%M')}")


def _send_activity_message(ws, df_acts, mask, text, role):
    """يحفظ الرسالة في العمود المناسب ويُحدّث الشيت."""
    import time
    entry = _format_new_comment(text, role)
    col   = "Admin_Comment" if role == "Admin" else "Owner_Comment"

    if col not in df_acts.columns:
        df_acts[col] = ""

    old = str(df_acts.loc[mask, col].values[0]).strip()
    df_acts.loc[mask, col] = _append_comment(old, entry)

    try:
        # تنظيف وحفظ
        df_clean = df_acts.fillna("").astype(object).where(
            pd.notnull(df_acts.fillna("")), ""
        )
        ws.update(
            values=[df_clean.columns.tolist()] + df_clean.values.tolist(),
            range_name="A1",
        )
        st.success("✅ تم إرسال الرسالة!")
        time.sleep(0.8)
        st.rerun()
    except Exception as e:
        st.error(f"خطأ في الحفظ: {e}")


# ──────────────────────────────────────────────
# الواجهة الرئيسية — مؤشر KPI
# ──────────────────────────────────────────────
def show_kpi_chat(
    ws_kpi,
    df_kpi: pd.DataFrame,
    kpi_name: str,
    current_role: str,
    current_user: str,
) -> None:
    """
    نفس المحادثة لكن مرتبطة بمؤشر KPI.
    الاستخدام:
        show_kpi_chat(ws_kpi, df_kpi, sel_kpi_name, "Admin", user_name)
    """
    mask = df_kpi["KPI_Name"].astype(str).str.strip() == kpi_name.strip()
    if not mask.any():
        st.warning("لم يُعثر على المؤشر.")
        return

    row        = df_kpi[mask].iloc[0]
    owner_text = str(row.get("Owner_Comment", "")).strip()
    admin_text = str(row.get("Admin_Comment", "")).strip()
    messages   = _merge_and_sort(owner_text, admin_text)

    short_kpi = kpi_name[:55] + "…" if len(kpi_name) > 55 else kpi_name
    st.markdown(f"#### 💬 محادثة المؤشر: {short_kpi}")

    n_admin = sum(1 for m in messages if m["role"] == "Admin")
    n_owner = sum(1 for m in messages if m["role"] == "Owner")
    c1, c2, c3 = st.columns(3)
    c1.metric("📨 إجمالي", len(messages))
    c2.metric("🔵 المدير",  n_admin)
    c3.metric("🟢 الموظف",  n_owner)
    st.markdown("---")

    chat_height = min(max(len(messages) * 80, 200), 500)
    with st.container(height=chat_height):
        _render_chat(messages, current_role)

    st.markdown("---")
    sender_label = "المدير" if current_role == "Admin" else "الموظف"
    new_msg = st.text_area(
        f"✍️ رسالة جديدة ({sender_label})",
        placeholder="اكتب ردك هنا...",
        height=90,
        key=f"kpi_chat_input_{kpi_name[:30]}",
    )

    col_send, _ = st.columns([2, 1])
    with col_send:
        if st.button("📤 إرسال", type="primary",
                     use_container_width=True,
                     key=f"kpi_chat_send_{kpi_name[:25]}"):
            if not new_msg.strip():
                st.warning("الرسالة فارغة.")
            else:
                _send_kpi_message(ws_kpi, df_kpi, mask, new_msg, current_role)


def _send_kpi_message(ws_kpi, df_kpi, mask, text, role):
    import time
    entry = _format_new_comment(text, role)
    col   = "Admin_Comment" if role == "Admin" else "Owner_Comment"
    if col not in df_kpi.columns:
        df_kpi[col] = ""
    old = str(df_kpi.loc[mask, col].values[0]).strip()
    df_kpi.loc[mask, col] = _append_comment(old, entry)
    try:
        df_clean = df_kpi.fillna("").astype(object).where(pd.notnull(df_kpi.fillna("")), "")
        ws_kpi.update(
            values=[df_clean.columns.tolist()] + df_clean.values.tolist(),
            range_name="A1",
        )
        st.success("✅ تم إرسال الرسالة!")
        time.sleep(0.8)
        st.rerun()
    except Exception as e:
        st.error(f"خطأ في الحفظ: {e}")
