"""Students: search your full attendance history by roll number (no login needed)."""
import pandas as pd
import streamlit as st

from core import attendance, components, database, ui

MIN_PERCENT = 75  # the usual minimum attendance

ui.setup("My History", "🗓️")
ui.inject_css()

st.title("🗓️ My Attendance History")
st.caption("Enter your roll number to see your percentage, graphs and every class date.")

with st.form("history_lookup"):
    roll_input = st.text_input("Roll number", value=st.session_state.get("history_roll", ""))
    searched = st.form_submit_button("Search", type="primary")
if searched:
    # Remembered so the results stay when you change a filter below.
    st.session_state["history_roll"] = roll_input.strip()

roll_no = st.session_state.get("history_roll", "")
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

c1, c2, c3, c4 = st.columns(4)
c1.metric("Overall attendance", f"{overall}%")
c2.metric("Classes held", held)
c3.metric("Present", attended)
c4.metric("Absent", held - attended)

if overall >= MIN_PERCENT:
    st.markdown(components.notice("ok", "You are above the minimum", f"Required: {MIN_PERCENT}%."),
                unsafe_allow_html=True)
else:
    st.markdown(components.notice("warn", f"Below {MIN_PERCENT}% attendance",
                                  f"The minimum required is {MIN_PERCENT}%."),
                unsafe_allow_html=True)

tab_graphs, tab_table = st.tabs(["📊 Graphs", "📋 History table"])

with tab_graphs:
    by_subject = df.groupby("subject")["present"].agg(attended="sum", held="count")
    by_subject["percent"] = (100 * by_subject["attended"] / by_subject["held"]).round(1)

    st.markdown("##### Attendance % by subject")
    st.bar_chart(by_subject["percent"])
    st.dataframe(
        by_subject.reset_index().rename(columns={
            "subject": "Subject", "attended": "Present", "held": "Classes held", "percent": "Percent"}),
        use_container_width=True, hide_index=True,
    )

    st.markdown("##### Attendance trend (running %)")
    daily = df.groupby("date")["present"].agg(attended="sum", held="count").sort_index()
    running = (100 * daily["attended"].cumsum() / daily["held"].cumsum()).round(1)
    running.index = pd.to_datetime(running.index)
    st.line_chart(running)
    st.caption("Each point is your overall attendance % after that day's classes.")

with tab_table:
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
            "⬇️ Download CSV", table.to_csv(index=False).encode("utf-8"),
            file_name=f"attendance_{student['roll_no']}.csv", mime="text/csv",
        )

    st.caption("Classes held = days on which attendance was taken for the subject, "
               "counted from the day you were registered.")