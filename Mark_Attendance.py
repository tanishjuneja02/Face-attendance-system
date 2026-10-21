"""Home page: students scan their face to mark attendance (no login needed)."""
import streamlit as st

from core import attendance, cache, components, database, face, photos, ui

ui.setup("Face Attendance", "📷")
ui.inject_css()

now = attendance.now_ist()
today = now.strftime("%Y-%m-%d")

st.markdown(
    components.hero(
        "Face Attendance",
        "Pick your subject, look at the camera, and you're marked present.",
        now.strftime("%A, %d %B %Y"),
    ),
    unsafe_allow_html=True,
)
@st.fragment
def scanner(subjects, students, today):
    """Only this part re-runs when you scan, pick a subject or toggle the camera."""
    stats_slot = st.empty()  # filled at the end so the numbers include this scan
    subject_names = {s["id"]: s["name"] for s in subjects}

    left, right = st.columns([1, 1.4], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("##### 1️⃣  Choose the subject")
            subject_id = st.selectbox(
                "Subject", list(subject_names), format_func=subject_names.get,
                label_visibility="collapsed",
            )
            st.markdown("##### :material/lightbulb: Tips for a good scan")
            st.markdown(
                "- Face the camera straight on\n"
                "- Keep the light in front of you, not behind\n"
                "- Remove your cap or mask\n"
                "- Only one person in the frame"
            )
    if "camera_on" not in st.session_state:
        st.session_state["camera_on"] = True

    with right:
        with st.container(border=True):
            st.markdown("##### 2️⃣  Scan your face")
            photo = None
            if st.session_state["camera_on"]:
                photo = st.camera_input("Scan your face", label_visibility="collapsed", key="scan_camera")
                if st.button(":material/stop_circle: Stop camera", use_container_width=True):
                    st.session_state["camera_on"] = False
                    st.rerun(scope="fragment")
            else:
                st.info("Camera is off.")
                if st.button(":material/play_arrow: Start camera", type="primary", use_container_width=True):
                    st.session_state["camera_on"] = True
                    st.rerun(scope="fragment")

    if photo is not None:
        error, result_match = None, None
        with st.spinner("Recognising face..."):
            try:
                embedding = face.get_scan_embedding(ui.read_image(photo))
                result_match = face.match_face(embedding, students)
            except face.FaceNotFoundError as exc:
                error = str(exc)
        match = result_match.match if result_match else None
        if error:
            st.markdown(components.notice("err", "No face detected", error), unsafe_allow_html=True)

        elif result_match.status == "ambiguous":
            st.markdown(
                components.notice("warn", "Could not tell who this is",
                                  "Your face is very close to another student's. Move closer, face the "
                                  "camera straight on in good light, and try again."),
                unsafe_allow_html=True,
            )

        elif match is None:
            st.markdown(
                components.notice("err", "Face not recognised",
                                  "Try again in better light, or ask the admin to register you."),
                unsafe_allow_html=True,
            )
        else:
            student = database.get_student(match.student_id)
            result = attendance.mark_attendance(student["id"], subject_id)

            if result.marked:
                cache.stats.clear()         # so the numbers below include this scan
                cache.recent_today.clear()
                st.markdown(
                    components.notice("ok", f"Attendance marked for {student['name']}",
                                      "You're all set. Have a great class!"),
                    unsafe_allow_html=True,
                )
                st.balloons()
            else:
                st.markdown(
                    components.notice("info", f"{student['name']} is already marked",
                                      f"Attendance for this subject was recorded today at {attendance.to_12h(result.time)}."),
                    unsafe_allow_html=True,
                )

            photo_col, details_col = st.columns([1, 2.2], gap="large")
            with photo_col:
                photo_bytes = photos.read_photo_bytes(student["photo_path"])
                if photo_bytes:
                    st.image(photo_bytes, caption="Registered photo", use_container_width=True)
            with details_col:
                st.markdown(
                    components.result_card(
                        student["name"], student["roll_no"], student["class_name"],
                        subject_names[subject_id], result.date, attendance.to_12h(result.time),
                    ),
                    unsafe_allow_html=True,
                )
                st.caption(f"Match distance: {match.distance:.2f} (lower is a closer match)")

    recent = [{**r, "time": attendance.to_12h(r["time"])} for r in cache.recent_today(today)]
    if recent:
        st.markdown("##### :material/schedule: Recent check-ins today")
        st.markdown(components.recent_list(recent), unsafe_allow_html=True)

    n_students, n_present = cache.stats(today)
    stats_slot.markdown(
        components.stats_row([
            ("🎓", "Registered students", n_students),
            ("✅", "Present today", n_present),
            ("📚", "Subjects", len(subjects)),
        ]),
        unsafe_allow_html=True,
    )


subjects = cache.subjects()
students = cache.students_with_embeddings()

if not subjects:
    st.markdown(components.notice("warn", "No subjects yet", "Staff must add subjects first."),
                unsafe_allow_html=True)
elif not students:
    st.markdown(components.notice("info", "No students registered yet",
                                  "Ask the admin to register students first."),
                unsafe_allow_html=True)
else:
    scanner(subjects, students, today)

st.sidebar.info("Teachers and admins: use **Staff Login** in the menu above.")