"""Bilingual, read-only Streamlit dashboard for observed USDT deposits."""
from __future__ import annotations
import json
import os
from decimal import Decimal
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Handasa Deposit Monitor | مراقبة الإيداعات", page_icon="📊", layout="wide")
lang = st.sidebar.radio("Language / اللغة", ["العربية", "English"], index=0)
ar = lang == "العربية"
T = {
    "title": "هانداسا — مراقبة الإيداعات" if ar else "Handasa — Deposit Monitor",
    "caption": "عرض قراءة فقط؛ لا توجد تحويلات أو توقيعات من هذه اللوحة" if ar else "Read-only view; this dashboard performs no transfers or signing",
    "total": "إجمالي الإيداعات المرصودة" if ar else "Total observed deposits",
    "count": "عدد الإيداعات" if ar else "Deposit count",
    "latest": "آخر كتلة" if ar else "Latest block",
    "table": "الإيداعات المرصودة" if ar else "Observed deposits",
    "empty": "لا توجد إيداعات مرصودة في ملف الحالة بعد." if ar else "No deposits have been observed in the state file yet.",
    "footer": "القيمة المعروضة هي مجموع سجلات Transfer المؤكدة التي تطابق العقد والعنوان المكوّنين في البيئة." if ar else "The displayed value is the sum of confirmed Transfer records matching the configured contract and address.",
    "none": "لا توجد بيانات" if ar else "No data",
}
st.title(T["title"])
st.caption(T["caption"])
rows = []
path = Path(os.environ.get("DEPOSIT_STATE_FILE", "data/deposits.jsonl"))
if path.exists():
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
amounts = [Decimal(row["amount_usdt"]) for row in rows]
col1, col2, col3 = st.columns(3)
col1.metric(T["total"], f"{sum(amounts, Decimal('0')):,.6f} USDT")
col2.metric(T["count"], str(len(rows)))
col3.metric(T["latest"], str(rows[-1]["block"]) if rows else T["none"])
if rows:
    st.subheader(T["table"])
    st.dataframe(rows, use_container_width=True)
else:
    st.info(T["empty"])
st.caption(T["footer"])
