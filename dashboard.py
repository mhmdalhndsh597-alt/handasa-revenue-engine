"""Streamlit read-only dashboard for observed USDT deposits."""
from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Handasa Deposit Monitor", page_icon="📊", layout="wide")
st.title("Handasa — مراقبة الإيداعات")
st.caption("عرض قراءة فقط؛ لا توجد تحويلات أو توقيعات من هذه اللوحة")

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
col1.metric("إجمالي الإيداعات المرصودة", f"{sum(amounts, Decimal('0')):,.6f} USDT")
col2.metric("عدد الإيداعات", str(len(rows)))
col3.metric("آخر كتلة", str(rows[-1]["block"]) if rows else "لا توجد بيانات")

if rows:
    st.subheader("الإيداعات المرصودة")
    st.dataframe(rows, use_container_width=True)
else:
    st.info("لا توجد إيداعات مرصودة في ملف الحالة بعد.")

st.caption("القيمة المعروضة هي مجموع سجلات Transfer المؤكدة التي تطابق العقد والعنوان المكوّنين في البيئة.")
