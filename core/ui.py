"""Small Streamlit helpers shared by all pages (page setup, login checks)."""
import numpy as np
import streamlit as st
from PIL import Image

from core import components, database


def setup(title, icon="🎓"):
    """Must be the first Streamlit call on every page."""
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")
    database.init_db()
    apply_theme()
    st.markdown(
        "<style>"
        "[data-testid='stHeaderActionElements']{display:none !important;}"
        "h1 a, h2 a, h3 a, h4 a, h5 a, h6 a{display:none !important;}"
        "</style>",
        unsafe_allow_html=True,
    )


def _remember_theme():
    st.session_state["theme_dark"] = st.session_state["dark_toggle"]


def apply_theme():
    """Sidebar Light/Dark switch. The choice is remembered when you change pages."""
    # A widget's own state is dropped when you open another page, so the choice is
    # copied into "theme_dark" (a normal session value) and used as the starting value.
    was_dark = st.session_state.get("theme_dark", True)
    label = ":material/dark_mode: Dark mode" if was_dark else ":material/light_mode: Light mode"
    dark = st.sidebar.toggle(
        label,
        value=was_dark,
        key="dark_toggle",
        on_change=_remember_theme,
    )
    if dark:
        st.markdown(components.DARK_CSS, unsafe_allow_html=True)


def inject_css():
    """Add the custom styles used by the home page."""
    st.markdown(components.CSS, unsafe_allow_html=True)


def read_image(uploaded_file):
    """Convert a Streamlit camera/upload file into an RGB numpy array."""
    return np.array(Image.open(uploaded_file).convert("RGB"))


def current_staff():
    return st.session_state.get("staff")


def require_staff(roles=("teacher", "admin")):
    """Stop the page unless a staff member with an allowed role is logged in."""
    staff = current_staff()
    if staff is None:
        st.warning("Please log in as staff to view this page.")
        st.page_link("pages/1_Staff_Login.py", label="Go to Staff Login", icon=":material/lock:")
        st.stop()
    if staff["role"] not in roles:
        st.error("Your account does not have access to this page.")
        st.stop()
    sidebar_user()
    return staff


def sidebar_user():
    staff = current_staff()
    if staff:
        st.sidebar.write(f":material/person: **{staff['username']}** ({staff['role']})")
        if st.sidebar.button("Log out"):
            st.session_state.pop("staff", None)
            st.rerun()
