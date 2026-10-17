"""Students: enter your roll number to see your attendance - summary, graphs and every class."""
import math

import pandas as pd
import streamlit as st

from core import attendance, charts, components, database, ui

MIN_PERCENT = 75  # the usual minimum attendance

ui.setup("My Attendance", "📈")
ui.inject_css()

st.title(":material/trending_up: My Attendance")
st.caption("Enter your roll number to see your percentage, graphs and every class date.")

with st.form("lookup"):
    roll_input = st.text_input("Roll number", value=st.session_state.get("my_roll", ""))
    searched = st.form_submit_button("Show my attendance", type="primary")
if searched:
    # Remembered so the results stay when you change a filter below.
    st.session_state["my_roll"] = roll_input.strip()

roll_no = st.session_state.get("my_roll", "")
if not roll_no:
    st.stop()

student = database.get_student_by_roll(roll_no)
if student is None or student["is_deleted"]:
    st.markdown(
        components.notice("err", "Roll number not found", "Check the number, or ask your teacher."),
        unsafe_allow_html=True,
    )
    st.stop()

st.subheader(f"{student['name']}  ·  {student['class_name']}  ·  Roll {student['roll_no']}")

history = database.get_attendance_history(student["id"])
if not history:
    st.info("No classes have been recorded yet.")
    st.stop()

df = pd.DataFrame(history)
held = len(df)
attended = int(df["present"].sum())
overall = round(100 * attended / held, 1)

tab_summary, tab_graphs, tab_history = st.tabs([":material/home: Summary", ":material/bar_chart: Graphs", ":material/list_alt: History"])

# ------------------------------------------------------------------ summary
with tab_summary:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall attendance", f"{overall}%")
    c2.metric("Classes held", held)
    c3.metric("Present", attended)
    c4.metric("Absent", held - attended)

    if overall >= MIN_PERCENT:
        st.markdown(components.notice("ok", "You are above the minimum",
                                      f"Required: {MIN_PERCENT}%. Keep it up!"),
                    unsafe_allow_html=True)
    else:
        needed = math.ceil((MIN_PERCENT * held - 100 * attended) / (100 - MIN_PERCENT))
        st.markdown(components.notice(
            "warn", f"Below {MIN_PERCENT}% attendance",
            f"Attend the next {needed} classes in a row to reach {MIN_PERCENT}%."),
            unsafe_allow_html=True)

    st.markdown("##### By subject")
    for _, r in charts.subject_frame(df, MIN_PERCENT).sort_values("subject").iterrows():
        flag = "" if r["status"] == "ok" else " :material/warning:"
        st.write(f"**{r['subject']}**: {r['attended']} of {r['held']} classes ({r['percent']}%){flag}")
        st.progress(min(r["percent"] / 100, 1.0))

# ------------------------------------------------------------------ graphs
with tab_graphs:
    left, right = st.columns([1, 1.4], gap="large")
    with left:
        st.markdown("##### Present vs absent")
        st.altair_chart(charts.donut_chart(df, overall), use_container_width=True)
    with right:
        st.markdown("##### Subjects")
        st.altair_chart(charts.subject_chart(df, MIN_PERCENT), use_container_width=True)
        st.caption(f"The dashed line is the {MIN_PERCENT}% minimum. Red bars are below it.")

    st.markdown("##### Day by day")
    st.altair_chart(charts.calendar_chart(df), use_container_width=True)
    st.caption("Each square is one day: green = present in all classes, red = absent, "
               "in between = present in some.")

# ------------------------------------------------------------------ history
with tab_history:
    subjects = ["All subjects", *sorted(df["subject"].unique())]
    f1, f2 = st.columns(2)
    pick = f1.selectbox("Subject", subjects)
    show = f2.selectbox("Show", ["All", "Present only", "Absent only"])

    view = df
    if pick != subjects[0]:
        view = view[view["subject"] == pick]
    if show == "Present only":
        view = view[view["present"]]
    elif show == "Absent only":
        view = view[~view["present"]]

    if view.empty:
        st.info("Nothing to show for this filter.")
    else:
        table = pd.DataFrame({
            "Date": view["date"],
            "Day": pd.to_datetime(view["date"]).dt.strftime("%A"),
            "Subject": view["subject"],
            "Status": view["present"].map({True: "✅ Present", False: "❌ Absent"}),
            "Time": view["time"].map(lambda t: attendance.to_12h(t) if pd.notna(t) else "—"),
        })
        st.dataframe(table, use_container_width=True, hide_index=True)
        st.download_button(
            ":material/download: Download CSV", table.to_csv(index=False).encode("utf-8"),
            file_name=f"attendance_{student['roll_no']}.csv", mime="text/csv",
        )

    st.caption("Classes held = days on which attendance was taken for the subject, "
               "counted from the day you were registered.")