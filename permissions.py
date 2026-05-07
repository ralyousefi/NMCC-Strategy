"""
permissions.py — نظام صلاحيات الحقول لـ NMCC Strategy System
الإصدار: 1.0

المبدأ:
  كل حقل في data_editor له ثلاث حالات:
    EDIT   — قابل للتعديل (يظهر أبيض)
    VIEW   — للاطلاع فقط (disabled، يظهر رمادي)
    HIDDEN — مخفي تماماً (لا يظهر)

  كل دور له خريطة صلاحيات مختلفة لكل جدول.

الأدوار الموجودة في النظام:
  Admin  — مدير، يرى كل شيء ويعدّل المستهدفات والملاحظات الإدارية
  Owner  — مالك المبادرة، يعدّل الإنجاز والتواريخ وتعليقاته فقط
  Viewer — للاطلاع فقط، لا يعدّل شيئاً
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import streamlit as st
import pandas as pd


# ══════════════════════════════════════════════
# 1. ثوابت الحالات
# ══════════════════════════════════════════════
EDIT   = "edit"
VIEW   = "view"
HIDDEN = "hidden"


# ══════════════════════════════════════════════
# 2. تعريف الصلاحيات لكل جدول ودور
# ══════════════════════════════════════════════

# ── جدول الأنشطة (Activities) ──
ACTIVITIES_PERMISSIONS: dict[str, dict[str, str]] = {
    #  حقل          Admin    Owner    Viewer
    "Mabadara":   {"Admin": HIDDEN, "Owner": HIDDEN,  "Viewer": HIDDEN},
    "Activity":   {"Admin": VIEW,   "Owner": VIEW,    "Viewer": VIEW},
    "Start_Date": {"Admin": VIEW,   "Owner": EDIT,    "Viewer": VIEW},
    "End_Date":   {"Admin": VIEW,   "Owner": EDIT,    "Viewer": VIEW},
    "Progress":   {"Admin": VIEW,   "Owner": EDIT,    "Viewer": VIEW},
    "Evidence_Link":{"Admin":VIEW,  "Owner": EDIT,    "Viewer": VIEW},
    "Owner_Comment":{"Admin":VIEW,  "Owner": VIEW,    "Viewer": VIEW},
    "Admin_Comment":{"Admin":VIEW,  "Owner": VIEW,    "Viewer": HIDDEN},
    # أعمدة وقتية — مخفية دائماً
    "_end":       {"Admin": HIDDEN, "Owner": HIDDEN,  "Viewer": HIDDEN},
    "New_Admin_Note":{"Admin":EDIT, "Owner": HIDDEN,  "Viewer": HIDDEN},
    "New_Owner_Note":{"Admin":HIDDEN,"Owner":EDIT,    "Viewer": HIDDEN},
}

# ── جدول المؤشرات (KPIs) ──
KPI_PERMISSIONS: dict[str, dict[str, str]] = {
    #  حقل           Admin    Owner    Viewer
    "KPI_Name":    {"Admin": VIEW,   "Owner": VIEW,   "Viewer": VIEW},
    "Target":      {"Admin": EDIT,   "Owner": VIEW,   "Viewer": VIEW},
    "Actual":      {"Admin": VIEW,   "Owner": EDIT,   "Viewer": VIEW},
    "Unit":        {"Admin": VIEW,   "Owner": VIEW,   "Viewer": VIEW},
    "Direction":   {"Admin": VIEW,   "Owner": VIEW,   "Viewer": VIEW},
    "Frequency":   {"Admin": VIEW,   "Owner": VIEW,   "Viewer": VIEW},
    "Owner":       {"Admin": EDIT,   "Owner": VIEW,   "Viewer": VIEW},
    "Owner_Comment":{"Admin":VIEW,   "Owner": VIEW,   "Viewer": VIEW},
    "Admin_Comment":{"Admin":VIEW,   "Owner": VIEW,   "Viewer": HIDDEN},
    "Category":    {"Admin": HIDDEN, "Owner": HIDDEN, "Viewer": HIDDEN},
    "New_Admin_Note":{"Admin":EDIT,  "Owner": HIDDEN, "Viewer": HIDDEN},
    "New_Owner_Note":{"Admin":HIDDEN,"Owner": EDIT,   "Viewer": HIDDEN},
}


# ══════════════════════════════════════════════
# 3. الدالة الرئيسية: تطبيق الصلاحيات
# ══════════════════════════════════════════════

@dataclass
class EditorConfig:
    """نتيجة apply_permissions — جاهزة للتمرير لـ st.data_editor."""
    df:            pd.DataFrame
    column_config: dict[str, Any]
    disabled:      list[str]


def apply_permissions(
    df: pd.DataFrame,
    permissions: dict[str, dict[str, str]],
    role: str,
    base_column_config: dict[str, Any] = None,
) -> EditorConfig:
    """
    يُطبّق خريطة الصلاحيات على DataFrame ويُرجع EditorConfig.

    المعاملات:
        df                 — DataFrame الأصلي
        permissions        — خريطة الصلاحيات (ACTIVITIES_PERMISSIONS أو KPI_PERMISSIONS)
        role               — دور المستخدم: "Admin" | "Owner" | "Viewer"
        base_column_config — إعدادات العمود الأساسية (عناوين، أنواع، عروض...)

    الاستخدام:
        cfg = apply_permissions(df_filt, ACTIVITIES_PERMISSIONS, role,
                                base_column_config=MY_COL_CONFIG)
        edited = st.data_editor(
            cfg.df,
            column_config=cfg.column_config,
            disabled=cfg.disabled,
            ...
        )
    """
    role = _normalize_role(role)
    cfg  = base_column_config.copy() if base_column_config else {}

    df_out   = df.copy()
    disabled = []

    for col in list(df_out.columns):
        perm = permissions.get(col, {}).get(role, VIEW)  # افتراضي: VIEW

        if perm == HIDDEN:
            # أخفِ العمود بـ None في column_config
            cfg[col] = None
        elif perm == VIEW:
            # أضفه لقائمة disabled
            disabled.append(col)
        # EDIT: لا تفعل شيئاً — يبقى قابلاً للتعديل

    # أضمن إخفاء الحقول غير الموجودة في permissions أيضاً
    for col in df_out.columns:
        if col not in permissions and col not in cfg:
            cfg[col] = None   # أخفِ أي عمود غير مذكور صراحةً

    return EditorConfig(df=df_out, column_config=cfg, disabled=disabled)


def _normalize_role(role: str) -> str:
    """يوحّد حالة الأحرف: admin→Admin, owner→Owner, ..."""
    mapping = {
        "admin":  "Admin",
        "owner":  "Owner",
        "viewer": "Viewer",
        "staff":  "Viewer",
    }
    return mapping.get(str(role).strip().lower(), "Viewer")


# ══════════════════════════════════════════════
# 4. أعمدة الصلاحيات الجاهزة (Base Configs)
# ══════════════════════════════════════════════

# ── الأعمدة الأساسية لجدول الأنشطة ──
ACTIVITIES_BASE_CONFIG = {
    "Activity":      st.column_config.TextColumn("النشاط", width="large"),
    "Start_Date":    st.column_config.DateColumn("تاريخ البداية", format="YYYY-MM-DD"),
    "End_Date":      st.column_config.DateColumn("تاريخ النهاية", format="YYYY-MM-DD"),
    "Progress":      st.column_config.ProgressColumn(
                         "الإنجاز %", format="%d%%", min_value=0, max_value=100),
    "Evidence_Link": st.column_config.LinkColumn("رابط الدليل", display_text="📎 فتح"),
    "Owner_Comment": st.column_config.TextColumn("تعليق الموظف", width="medium"),
    "Admin_Comment": st.column_config.TextColumn("ملاحظة المدير", width="medium"),
    "New_Admin_Note":st.column_config.TextColumn("✍️ ملاحظة المدير الجديدة", width="large"),
    "New_Owner_Note":st.column_config.TextColumn("✍️ ملاحظتي الجديدة", width="large"),
}

# ── الأعمدة الأساسية لجدول المؤشرات ──
KPI_BASE_CONFIG = {
    "KPI_Name":      st.column_config.TextColumn("المؤشر", width="large"),
    "Target":        st.column_config.NumberColumn("المستهدف", required=True),
    "Actual":        st.column_config.NumberColumn("المتحقق"),
    "Unit":          st.column_config.TextColumn("الوحدة"),
    "Direction":     st.column_config.TextColumn("الاتجاه"),
    "Owner":         st.column_config.TextColumn("المسؤول"),
    "Owner_Comment": st.column_config.TextColumn("تعليق المالك", width="medium"),
    "Admin_Comment": st.column_config.TextColumn("سجل المدير", width="medium"),
    "New_Admin_Note":st.column_config.TextColumn("✍️ ملاحظة المدير الجديدة", width="large"),
    "New_Owner_Note":st.column_config.TextColumn("✍️ ملاحظتي الجديدة (تُرسل للمدير)", width="large"),
}


# ══════════════════════════════════════════════
# 5. دوال مساعدة للواجهة
# ══════════════════════════════════════════════

def get_current_role() -> str:
    """يُرجع دور المستخدم الحالي من session_state."""
    return str(st.session_state.get('user_info', {}).get('role', 'Viewer')).strip()


def permission_badge(role: str) -> None:
    """يعرض شارة صغيرة توضح الصلاحية الحالية."""
    role_n = _normalize_role(role)
    config = {
        "Admin":  ("🔴 مدير — صلاحيات كاملة",      "#fde8e8", "#c0392b"),
        "Owner":  ("🟡 مالك — تعديل بياناتي فقط",   "#fef9e7", "#d35400"),
        "Viewer": ("🟢 مشاهد — للاطلاع فقط",         "#eafaf1", "#1e8449"),
    }
    label, bg, color = config.get(role_n, ("غير معروف", "#f3f3f3", "#555"))
    st.markdown(
        f"<div style='background:{bg};color:{color};border-right:4px solid {color};"
        f"border-radius:6px;padding:6px 14px;font-size:13px;font-weight:bold;"
        f"display:inline-block;margin-bottom:10px;direction:rtl'>{label}</div>",
        unsafe_allow_html=True,
    )


def field_legend(role: str, permissions: dict) -> None:
    """يعرض مفتاح الألوان للحقول القابلة للتعديل."""
    role_n = _normalize_role(role)
    editable = [col for col, perms in permissions.items()
                if perms.get(role_n) == EDIT]
    if not editable:
        return
    labels = {
        "Progress":       "نسبة الإنجاز %",
        "Start_Date":     "تاريخ البداية",
        "End_Date":       "تاريخ النهاية",
        "Evidence_Link":  "رابط الدليل",
        "New_Owner_Note": "ملاحظتك الجديدة",
        "New_Admin_Note": "ملاحظة المدير",
        "Target":         "المستهدف",
        "Actual":         "القيمة المتحققة",
        "Owner":          "اسم المسؤول",
    }
    readable = [labels.get(c, c) for c in editable if c in labels]
    if readable:
        st.caption(f"✏️ الحقول القابلة للتعديل: **{' | '.join(readable)}**")


# ══════════════════════════════════════════════
# 6. دالة الحفظ الموحّدة مع التحقق من الصلاحية
# ══════════════════════════════════════════════

def get_editable_fields(
    permissions: dict[str, dict[str, str]],
    role: str,
) -> list[str]:
    """يُرجع قائمة الحقول التي يحق لهذا الدور تعديلها."""
    role_n = _normalize_role(role)
    return [col for col, perms in permissions.items()
            if perms.get(role_n) == EDIT]


def safe_update_row(
    df_source: pd.DataFrame,
    edited_row: pd.Series,
    match_mask: pd.Series,
    permissions: dict[str, dict[str, str]],
    role: str,
) -> tuple[pd.DataFrame, list[str]]:
    """
    يُحدِّث الصفوف في df_source بناءً على edited_row،
    لكن فقط للحقول التي يملك هذا الدور صلاحية تعديلها.

    يُرجع: (df_محدَّث, قائمة_الحقول_التي_تغيّرت)
    """
    allowed = get_editable_fields(permissions, role)
    changed = []
    for col in allowed:
        if col in edited_row.index and col in df_source.columns:
            new_val = edited_row[col]
            old_val = df_source.loc[match_mask, col].values[0] \
                      if match_mask.any() else None
            # تجاهل القيم الفارغة في أعمدة الملاحظات الجديدة
            if col in ("New_Admin_Note", "New_Owner_Note"):
                continue   # تُعالَج بشكل خاص خارج هذه الدالة
            if str(new_val) != str(old_val):
                df_source.loc[match_mask, col] = new_val
                changed.append(col)
    return df_source, changed
