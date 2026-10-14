"""Staff login (teacher/admin). Also creates the very first admin account."""
import streamlit as st

from core import auth, database, ui

ui.setup("Staff Login", "🔐")
st.title("🔐 Staff Login")

staff = ui.current_staff()
if staff:
    st.success(f"Logged in as **{staff['username']}** ({staff['role']}).")
    st.page_link("pages/2_Attendance.py", label="View attendance", icon="📊")
    if staff["role"] == "admin":
        st.page_link("pages/3_Register.py", label="Register students and manage staff", icon="🧑‍🎓")
    if st.button("Log out"):
        st.session_state.pop("staff", None)
        st.rerun()
    st.stop()

if not auth.has_admin():
    st.info("First-time setup: create the admin account.")
    with st.form("first_admin"):
        username = st.text_input("Admin username")
        password = st.text_input("Password (min 6 characters)", type="password")
        if st.form_submit_button("Create admin"):
            try:
                auth.create_staff(username, password, "admin")
                st.success("Admin created. You can log in now.")
                st.rerun()
            except (ValueError, database.DuplicateError) as exc:
                st.error(str(exc))
    st.stop()

with st.form("login"):
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.form_submit_button("Log in"):
        user = auth.authenticate(username, password)
        if user:
            st.session_state["staff"] = user
            st.rerun()
        else:
            st.error("Wrong username or password.")
