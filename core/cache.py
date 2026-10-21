"""Cached read helpers so Streamlit reruns don't hit Turso every time."""
import streamlit as st

from core import database


@st.cache_data(ttl=600, show_spinner=False)
def subjects():
    return database.list_subjects()


@st.cache_data(ttl=600, show_spinner=False)
def students_with_embeddings():
    return database.get_students_with_embeddings()


@st.cache_data(ttl=20, show_spinner=False)
def stats(today):
    return database.count_students(), database.count_present_on(today)


@st.cache_data(ttl=20, show_spinner=False)
def recent_today(today):
    return database.get_attendance(start_date=today, end_date=today)[:5]


def clear_all():
    st.cache_data.clear()