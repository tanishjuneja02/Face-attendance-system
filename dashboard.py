import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Face Attendance Dashboard", layout="wide")

st.title("📋 Face Recognition Attendance System")

ATTENDANCE_FILE = "attendance.csv"

if not os.path.exists(ATTENDANCE_FILE):
    st.warning("No attendance records yet. Run recognize_faces.py first.")
else:
    df = pd.read_csv(ATTENDANCE_FILE)

    # Sidebar filters
    st.sidebar.header("Filters")
    unique_dates = sorted(df["Date"].unique(), reverse=True)
    selected_date = st.sidebar.selectbox("Select Date", ["All"] + list(unique_dates))

    unique_names = sorted(df["Name"].unique())
    selected_name = st.sidebar.selectbox("Select Person", ["All"] + list(unique_names))

    # Apply filters
    filtered_df = df.copy()
    if selected_date != "All":
        filtered_df = filtered_df[filtered_df["Date"] == selected_date]
    if selected_name != "All":
        filtered_df = filtered_df[filtered_df["Name"] == selected_name]

    # Today's summary
    today = datetime.now().strftime("%Y-%m-%d")
    today_df = df[df["Date"] == today]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Records", len(df))
    col2.metric("Today's Attendance", len(today_df))
    col3.metric("Unique People", df["Name"].nunique())

    st.subheader("Attendance Records")
    st.dataframe(filtered_df, use_container_width=True)

    # Download button
    csv_data = filtered_df.to_csv(index=False)
    st.download_button(
        label="Download as CSV",
        data=csv_data,
        file_name=f"attendance_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

    # Simple bar chart of attendance count per person
    st.subheader("Attendance Count by Person")
    st.bar_chart(df["Name"].value_counts())