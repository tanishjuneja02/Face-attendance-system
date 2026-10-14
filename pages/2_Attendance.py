"""Teacher/admin: view, filter and download attendance."""
from datetime import timedelta

import pandas as pd
import streamlit as st

from core import attendance, database, ui

ui.setup("Attendance Records", "📊")
ui.require_staff()

st.title("📊 Attendance Records")

today = attendance.now_ist().date()
subjects = {s["id"]: s["name"] for s in database.list_subjects()}
classes = sorted({s["class_name"] for s in database.list_students()})

col1, col2, col3, col4 = st.columns(4)
date_range = col1.date_input("Date range", value=(today - timedelta(days=7), today))
subject_id = col2.selectbox("Subject", [None, *subjects], format_func=lambda x: "All" if x is None else subjects[x])
class_name = col3.selectbox("Class", [None, *classes], format_func=lambda x: "All" if x is None else x)
roll_no = col4.text_input("Roll number (optional)")

start = end = None
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = (d.strftime("%Y-%m-%d") for d in date_range)

rows = database.get_attendance(
    start_date=start, end_date=end, subject_id=subject_id,
    class_name=class_name, roll_no=roll_no.strip() or None,
)
df = pd.DataFrame(rows, columns=["roll_no", "name", "class_name", "subject", "date", "time"])
df.columns = ["Roll No", "Name", "Class", "Subject", "Date", "Time"]
df["Time"] = df["Time"].map(attendance.to_12h)  # show 12-hour time

m1, m2, m3 = st.columns(3)
m1.metric("Records", len(df))
m2.metric("Students present", df["Roll No"].nunique())
m3.metric("Today", int((df["Date"] == today.strftime("%Y-%m-%d")).sum()))

if df.empty:
    st.info("No attendance records for these filters.")
else:
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Download CSV",
        df.to_csv(index=False),
        file_name=f"attendance_{today:%Y%m%d}.csv",
        mime="text/csv",
    )
    st.subheader("Records per subject")
    st.bar_chart(df["Subject"].value_counts())
