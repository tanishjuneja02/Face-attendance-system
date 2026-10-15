"""Students: enter your roll number to see your own attendance (no login needed)."""
import math

import streamlit as st

from core import components, database, ui

MIN_PERCENT = 75  # the usual minimum attendance

ui.setup("My Attendance", "📈")
ui.inject_css()

st.title("📈 My Attendance")
st.caption("Enter your roll number to see how many classes you have attended.")

with st.form("lookup"):
    roll_no = st.text_input("Roll number")
    look = st.form_submit_button("Show my attendance", type="primary")

if look:
    student = database.get_student_by_roll(roll_no) if roll_no.strip() else None
    if student is None or student["is_deleted"]:
        st.markdown(
            components.notice("err", "Roll number not found",
                              "Check the number, or ask your teacher."),
            unsafe_allow_html=True,
        )
    else:
        rows = database.get_attendance_summary(student["id"])
        st.subheader(f"{student['name']}  ·  {student['class_name']}")
        if not rows:
            st.info("No classes have been recorded yet.")
        else:
            attended = sum(r["attended"] for r in rows)
            held = sum(r["total"] for r in rows)
            overall = round(100 * attended / held, 1)

            c1, c2, c3 = st.columns(3)
            c1.metric("Overall attendance", f"{overall}%")
            c2.metric("Classes attended", attended)
            c3.metric("Classes held", held)

            if overall >= MIN_PERCENT:
                st.markdown(
                    components.notice("ok", "You are above the minimum",
                                      f"Required: {MIN_PERCENT}%. Keep it up!"),
                    unsafe_allow_html=True,
                )
            else:
                needed = math.ceil((MIN_PERCENT * held - 100 * attended) / (100 - MIN_PERCENT))
                st.markdown(
                    components.notice(
                        "warn", f"Below {MIN_PERCENT}% attendance",
                        f"Attend the next {needed} classes in a row to reach {MIN_PERCENT}%."),
                    unsafe_allow_html=True,
                )

            st.markdown("##### By subject")
            for r in rows:
                flag = "" if r["percent"] >= MIN_PERCENT else " ⚠️"
                st.write(f"**{r['subject']}**: {r['attended']} of {r['total']} classes "
                         f"({r['percent']}%){flag}")
                st.progress(min(r["percent"] / 100, 1.0))

        st.caption("Classes held = days on which attendance was taken for the subject, "
                   "counted from the day you were registered.")