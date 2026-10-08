import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    return datetime.now(IST)

st.set_page_config(page_title="Face Attendance System", page_icon="🎓", layout="wide")
st.markdown("""
<style>
    .main { padding-top: 1rem; }
    [data-testid="stSidebar"] {
        background-color: #1a1a2e;
    }
    h1 {
        color: #4CAF50;
    }

    .stButton button {
        border-radius: 8px;
        font-weight: 600;
    }
    [data-testid="stMetricValue"] {
        font-size: 28px;
    }
    [data-testid="stMetric"] {
        background-color: rgba(76, 175, 80, 0.08);
        border-radius: 10px;
        padding: 10px;
    }
    div[data-testid="stExpander"] {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

DB_FILE = "attendance_system.db"

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False, timeout=10)


def init_db():
    # Unconditionally start fresh if the file looks suspicious or on every cold start
    if os.path.exists(DB_FILE):
        try:
            test_conn = sqlite3.connect(DB_FILE)
            test_cursor = test_conn.cursor()
            test_cursor.execute("PRAGMA integrity_check")
            result = test_cursor.fetchone()
            test_conn.close()
            if result is None or result[0] != "ok":
                os.remove(DB_FILE)
        except sqlite3.DatabaseError:
            try:
                test_conn.close()
            except Exception:
                pass
            os.remove(DB_FILE)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'student')),
            full_name TEXT NOT NULL,
            is_deleted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if "is_deleted" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN is_deleted INTEGER DEFAULT 0")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects(id),
            UNIQUE(subject_id, date)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            subject_id INTEGER REFERENCES subjects(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    for subject in ["Mathematics", "Physics", "Chemistry", "English", "Computer Science"]:
        cursor.execute("SELECT * FROM subjects WHERE name = ?", (subject,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO subjects (name) VALUES (?)", (subject,))

    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (username, password, role, full_name, is_deleted)
            VALUES (?, ?, ?, ?, 0)
        """, ("admin", "admin123", "admin", "System Admin"))

    conn.commit()
    conn.close()

init_db()

def check_login(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, full_name FROM users WHERE username = ? AND password = ? AND is_deleted = 0", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

# ---------- LOGIN PAGE ----------
if not st.session_state.logged_in:
    st.title("🎓 Face Attendance System")
    st.caption(f"📅 {now_ist().strftime('%A, %d %B %Y')}")
    st.divider()
    st.subheader("🔐 Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            user = check_login(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = {
                    "id": user[0],
                    "username": user[1],
                    "role": user[2],
                    "full_name": user[3]
                }
                st.rerun()
            else:
                st.error("Invalid username or password.")

else:
    # ---------- LOGGED IN ----------
    user = st.session_state.user

    st.sidebar.markdown("### 🎓 SmartAttend")
    st.sidebar.divider()
    st.sidebar.write(f"👤 **{user['full_name']}**")
    st.sidebar.write(f"🏷️ {user['role'].capitalize()}")
    st.sidebar.divider()
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

    if user["role"] == "admin":
        st.header("Admin Dashboard")
        st.caption("Manage users, register faces, and monitor attendance across the institution.")

        conn = get_connection()
        today_str = now_ist().strftime("%Y-%m-%d")
        today_count = pd.read_sql_query(
            "SELECT COUNT(*) as c FROM attendance WHERE date = ?", conn, params=(today_str,)
        )["c"].values[0]
        total_users = pd.read_sql_query("SELECT COUNT(*) as c FROM users WHERE is_deleted = 0", conn)["c"].values[0]
        conn.close()

        col1, col2 = st.columns(2)
        col1.metric("Today's Attendance Marks", int(today_count))
        col2.metric("Total Active Users", int(total_users))
        st.divider()

        tab1, tab2 = st.tabs(["👥 Manage Users", "📊 All Attendance"])
        with tab1:
            with st.expander("➕ Add New User", expanded=False):
                face_method = st.radio(
                    "How do you want to capture their face?",
                    ["Upload a photo", "Use camera"],
                    key="face_method_choice"
                )

                with st.form("add_user_form"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        new_username = st.text_input("Username")
                    with col_b:
                        new_password = st.text_input("Password")
                    new_fullname = st.text_input("Full Name")
                    new_role = st.selectbox("Role", ["student", "teacher", "admin"])

                    face_label = "Upload a clear face photo (required for students)" if new_role == "student" else "Upload a face photo (optional)"
                    if face_method == "Upload a photo":
                        face_file = st.file_uploader(face_label, type=["jpg", "jpeg", "png"])
                    else:
                        face_file = st.camera_input("Take a photo of the person's face (optional)")

                    add_submitted = st.form_submit_button("Add User")

                    if add_submitted:
                        if new_username and new_password and new_fullname:
                            if new_role == "student" and face_file is None:
                                st.warning("Please provide a face photo for this student before adding them.")
                            else:
                                conn = get_connection()
                                cursor = conn.cursor()
                                try:
                                    cursor.execute(
                                        "INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)",
                                        (new_username, new_password, new_role, new_fullname)
                                    )
                                    conn.commit()

                                    if face_file is not None:
                                        os.makedirs("known_faces", exist_ok=True)
                                        filepath = f"known_faces/{new_username}.jpg"
                                        with open(filepath, "wb") as f:
                                            f.write(face_file.getbuffer())
                                        st.success(f"User '{new_username}' added as {new_role}, with face registered.")
                                    else:
                                        st.success(f"User '{new_username}' added as {new_role}.")
                                except sqlite3.IntegrityError:
                                    st.error("Username already exists.")
                                conn.close()
                        else:
                            st.warning("Please fill in all fields.")

            st.divider()
            st.subheader("Existing Users")
            conn = get_connection()
            users_df = pd.read_sql_query(
                "SELECT id, username, full_name, role FROM users WHERE is_deleted = 0", conn
            )
            conn.close()

            users_df["display_name"] = users_df.apply(
                lambda r: f"{'👑' if r['role']=='admin' else '🧑‍🏫' if r['role']=='teacher' else '🎓'} {r['full_name']}", axis=1
            )

            st.dataframe(
                users_df[["id", "username", "display_name", "role"]].rename(columns={"display_name": "full_name"}),
                use_container_width=True, hide_index=True
            )

            st.divider()
            st.subheader("✏️ Edit or 🗑️ Delete a User")

            if users_df.empty:
                st.info("No users yet.")
            else:
                user_labels = [
                    f"{row['full_name']} ({row['username']}) — id:{row['id']}"
                    for _, row in users_df.iterrows()
                ]
                label_to_id = {
                    label: row["id"] for label, (_, row) in zip(user_labels, users_df.iterrows())
                }

                selected_label = st.selectbox(
                    "Select a user to manage",
                    options=user_labels,
                    key="manage_user_select"
                )
                manage_user_id = label_to_id[selected_label]
                selected_row = users_df[users_df["id"] == manage_user_id].iloc[0]

                st.caption(f"Managing: **{selected_row['full_name']}** (username: {selected_row['username']}, id: {manage_user_id})")

                col_edit, col_delete = st.columns(2)

                with col_edit:
                    st.markdown("**Edit Details**")
                    with st.form(f"edit_user_form_{manage_user_id}"):
                        edit_fullname = st.text_input("Full Name", value=selected_row["full_name"])
                        edit_role = st.selectbox(
                            "Role", ["student", "teacher", "admin"],
                            index=["student", "teacher", "admin"].index(selected_row["role"])
                        )
                        edit_password = st.text_input("New Password (leave blank to keep current)", type="password")
                        edit_face = st.file_uploader("Update face photo (optional)", type=["jpg", "jpeg", "png"], key=f"edit_face_{manage_user_id}")
                        edit_submitted = st.form_submit_button("Save Changes")

                        if edit_submitted:
                            conn = get_connection()
                            cursor = conn.cursor()
                            if edit_password:
                                cursor.execute(
                                    "UPDATE users SET full_name = ?, role = ?, password = ? WHERE id = ?",
                                    (edit_fullname, edit_role, edit_password, manage_user_id)
                                )
                            else:
                                cursor.execute(
                                    "UPDATE users SET full_name = ?, role = ? WHERE id = ?",
                                    (edit_fullname, edit_role, manage_user_id)
                                )
                            conn.commit()
                            conn.close()

                            if edit_face is not None:
                                os.makedirs("known_faces", exist_ok=True)
                                filepath = f"known_faces/{selected_row['username']}.jpg"
                                with open(filepath, "wb") as f:
                                    f.write(edit_face.getbuffer())

                            st.success(f"Updated {selected_row['username']} (id: {manage_user_id}).")
                            st.rerun()

                with col_delete:
                    st.markdown("**Delete User**")
                    st.warning(f"This will deactivate **{selected_row['full_name']}** (id: {manage_user_id}). You can restore them later from 'Recently Deleted' below.")
                    confirm_delete = st.checkbox(
                        f"Yes, deactivate {selected_row['full_name']}",
                        key=f"confirm_delete_{manage_user_id}"
                    )

                    if st.button("🗑️ Delete User", key=f"delete_btn_{manage_user_id}", disabled=not confirm_delete):
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE users SET is_deleted = 1 WHERE id = ?", (manage_user_id,))
                        conn.commit()
                        conn.close()

                        st.success(f"Deactivated {selected_row['full_name']} (id: {manage_user_id}).")
                        st.rerun()

            # ---- Recently Deleted / Restore ----
            st.divider()
            st.subheader("♻️ Recently Deleted Users")
            conn = get_connection()
            deleted_df = pd.read_sql_query(
                "SELECT id, username, full_name, role FROM users WHERE is_deleted = 1", conn
            )
            conn.close()

            if deleted_df.empty:
                st.caption("No deleted users.")
            else:
                st.dataframe(deleted_df, use_container_width=True, hide_index=True)

                restore_labels = [
                    f"{row['full_name']} ({row['username']}) — id:{row['id']}"
                    for _, row in deleted_df.iterrows()
                ]
                restore_label_to_id = {
                    label: row["id"] for label, (_, row) in zip(restore_labels, deleted_df.iterrows())
                }
                restore_choice = st.selectbox("Select a user to restore", options=restore_labels, key="restore_select")
                restore_id = restore_label_to_id[restore_choice]
                restore_row = deleted_df[deleted_df["id"] == restore_id].iloc[0]

                col_restore, col_perm_delete = st.columns(2)

                with col_restore:
                    if st.button("♻️ Restore This User", key="restore_btn"):
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE users SET is_deleted = 0 WHERE id = ?", (restore_id,))
                        conn.commit()
                        conn.close()
                        st.success("User restored.")
                        st.rerun()

                with col_perm_delete:
                    st.caption("⚠️ This cannot be undone.")
                    confirm_perm_delete = st.checkbox(
                        f"Yes, permanently delete {restore_row['full_name']}",
                        key=f"confirm_perm_delete_{restore_id}"
                    )
                    if st.button("🔥 Delete Permanently", key=f"perm_delete_btn_{restore_id}", disabled=not confirm_perm_delete):
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM attendance WHERE user_id = ?", (restore_id,))
                        cursor.execute("DELETE FROM users WHERE id = ?", (restore_id,))
                        conn.commit()
                        conn.close()

                        face_path = f"known_faces/{restore_row['username']}.jpg"
                        if os.path.exists(face_path):
                            os.remove(face_path)

                        st.success(f"Permanently deleted {restore_row['full_name']}.")
                        st.rerun()

        with tab2:
            st.subheader("All Attendance Records")
            conn = get_connection()
            att_df = pd.read_sql_query("""
                SELECT users.full_name, users.role, attendance.date, attendance.time
                FROM attendance
                JOIN users ON attendance.user_id = users.id
                ORDER BY attendance.date DESC, attendance.time DESC
            """, conn)
            conn.close()
            col1, col2 = st.columns(2)
            col1.metric("Total Records", len(att_df))
            col2.metric("Unique Students", att_df["full_name"].nunique() if not att_df.empty else 0)

            st.dataframe(att_df, use_container_width=True)

    elif user["role"] == "teacher":
        st.header("Teacher Dashboard")
        st.caption("Mark attendance by subject, register student faces, and review records.")

        tab1, tab2 = st.tabs(["✅ Mark Attendance","📊 View Attendance"])

        # ---- TAB 1: Mark Attendance ----
        with tab1:
            with st.expander("✅ Mark Attendance for a Subject", expanded=True):
                conn = get_connection()
                subjects_df = pd.read_sql_query("SELECT id, name FROM subjects", conn)
                students_df = pd.read_sql_query("SELECT id, full_name FROM users WHERE role = 'student'", conn)
                conn.close()

                selected_subject = st.selectbox(
                    "Select Subject",
                    options=subjects_df["id"],
                    format_func=lambda x: subjects_df[subjects_df["id"] == x]["name"].values[0]
                )

                selected_students = st.multiselect(
                    "Select Students Present Today",
                    options=students_df["id"],
                    format_func=lambda x: students_df[students_df["id"] == x]["full_name"].values[0]
                )

                if st.button("Mark Attendance"):
                    if selected_students:
                        conn = get_connection()
                        cursor = conn.cursor()
                        now = now_ist()
                        today = now.strftime("%Y-%m-%d")
                        time_now = now.strftime("%H:%M:%S")

                        cursor.execute("""
                            INSERT OR IGNORE INTO classes (subject_id, date)
                            VALUES (?, ?)
                        """, (selected_subject, today))

                        marked_count = 0
                        for student_id in selected_students:
                            cursor.execute("""
                                SELECT * FROM attendance
                                WHERE user_id = ? AND subject_id = ? AND date = ?
                            """, (student_id, selected_subject, today))
                            if not cursor.fetchone():
                                cursor.execute("""
                                    INSERT INTO attendance (user_id, date, time, subject_id)
                                    VALUES (?, ?, ?, ?)
                                """, (student_id, today, time_now, selected_subject))
                                marked_count += 1

                        conn.commit()
                        conn.close()
                        st.success(f"Attendance marked for {marked_count} student(s).")
                    else:
                        st.warning("Select at least one student.")



        # ---- TAB 2 : View Attendance ----
        with tab2:
            st.subheader("Student Attendance Records")
            conn = get_connection()
            att_df = pd.read_sql_query("""
                SELECT users.full_name, subjects.name AS subject, attendance.date, attendance.time
                FROM attendance
                JOIN users ON attendance.user_id = users.id
                JOIN subjects ON attendance.subject_id = subjects.id
                WHERE users.role = 'student'
                ORDER BY attendance.date DESC, attendance.time DESC
            """, conn)
            conn.close()
            st.dataframe(att_df, use_container_width=True)

    elif user["role"] == "student":
        st.header("Student Dashboard")
        st.caption("Scan your face to mark attendance and track your progress by subject.")

        tab_scan, tab_overview, tab_subjects, tab_calendar = st.tabs(
            ["📷 Scan Attendance", "📊 Overview", "📚 By Subject", "📅 Calendar & Log"]
        )

        with tab_scan:
            st.subheader("Scan My Attendance")

            conn = get_connection()
            subjects_df = pd.read_sql_query("SELECT id, name FROM subjects", conn)
            conn.close()

            scan_subject = st.selectbox(
                "Select Subject",
                options=subjects_df["id"],
                format_func=lambda x: subjects_df[subjects_df["id"] == x]["name"].values[0],
                key="scan_subject"
            )

            st.info(f"📚 Marking attendance for: **{subjects_df[subjects_df['id'] == scan_subject]['name'].values[0]}**")

            if "show_camera" not in st.session_state:
                st.session_state.show_camera = True

            col_cam_toggle, _ = st.columns([1, 4])
            with col_cam_toggle:
                if st.session_state.show_camera:
                    if st.button("🛑 Stop Camera"):
                        st.session_state.show_camera = False
                        st.rerun()
                else:
                    if st.button("📷 Start Camera"):
                        st.session_state.show_camera = True
                        st.rerun()

            captured_photo = None
            if st.session_state.show_camera:
                captured_photo = st.camera_input("Take a photo to mark your attendance")

            if captured_photo is not None:
                known_path = f"known_faces/{user['username']}.jpg"

                if not os.path.exists(known_path):
                    st.error("No registered face found for your account. Ask admin/teacher to register your face first.")
                else:
                    with open("temp_scan.jpg", "wb") as f:
                        f.write(captured_photo.getbuffer())

                    with st.spinner("Verifying your face..."):
                        from deepface import DeepFace
                        try:
                            result = DeepFace.verify(
                                img1_path="temp_scan.jpg",
                                img2_path=known_path,
                                enforce_detection=False,
                                detector_backend="mtcnn"
                            )
                        except Exception as e:
                            result = None
                            st.error(f"Face verification failed: {e}")

                    if result:
                        if result["verified"]:
                            today = now_ist().strftime("%Y-%m-%d")
                            time_now = now_ist().strftime("%H:%M:%S")

                            conn = get_connection()
                            cursor = conn.cursor()

                            cursor.execute("""
                                INSERT OR IGNORE INTO classes (subject_id, date)
                                VALUES (?, ?)
                            """, (scan_subject, today))

                            cursor.execute("""
                                SELECT * FROM attendance
                                WHERE user_id = ? AND subject_id = ? AND date = ?
                            """, (user["id"], scan_subject, today))

                            if cursor.fetchone():
                                st.warning("You've already marked attendance for this subject today.")
                            else:
                                cursor.execute("""
                                    INSERT INTO attendance (user_id, subject_id, date, time)
                                    VALUES (?, ?, ?, ?)
                                """, (user["id"], scan_subject, today, time_now))
                                conn.commit()
                                st.toast("Attendance marked successfully!", icon="🎉")
                                st.success("✅ Attendance marked successfully for today!")
                                st.balloons()
                                st.session_state.show_camera = False
                            conn.close()
                        else:
                            st.error("Face did not match your registered photo. Try again with better lighting.")

                    if os.path.exists("temp_scan.jpg"):
                        os.remove("temp_scan.jpg")

        # Load data once, used across the remaining student tabs
        conn = get_connection()
        my_attendance = pd.read_sql_query("""
            SELECT subjects.name AS subject, attendance.date, attendance.time
            FROM attendance
            JOIN subjects ON attendance.subject_id = subjects.id
            WHERE attendance.user_id = ?
            ORDER BY attendance.date DESC
        """, conn, params=(user["id"],))

        held = pd.read_sql_query("""
            SELECT subjects.name AS subject,
                   COUNT(DISTINCT classes.date) AS classes_held
            FROM classes
            JOIN subjects ON classes.subject_id = subjects.id
            GROUP BY subjects.name
        """, conn)
        conn.close()

        if not held.empty:
            attended = (
                my_attendance.groupby("subject")["date"].nunique()
                .reset_index(name="classes_attended")
            )
            summary = held.merge(attended, on="subject", how="left")
            summary["classes_attended"] = summary["classes_attended"].fillna(0).astype(int)
            summary["percentage"] = (
                summary["classes_attended"] / summary["classes_held"] * 100
            ).round(1)

        with tab_overview:
            if held.empty:
                st.info("No classes have been held yet.")
            else:
                total_held = int(summary["classes_held"].sum())
                total_attended = int(summary["classes_attended"].sum())
                overall_pct = round(total_attended / total_held * 100, 1) if total_held else 0.0

                st.subheader("📊 Overall Attendance")
                col1, col2, col3 = st.columns(3)
                col1.metric(
                    "Overall Percentage",
                    f"{overall_pct}%",
                    delta=f"{overall_pct - 75:.1f}% vs 75% target",
                    delta_color="normal" if overall_pct >= 75 else "inverse"
                )
                col2.metric("Classes Attended", f"{total_attended} / {total_held}")
                col3.metric("Subjects", len(summary))
                st.progress(min(overall_pct / 100, 1.0))

                if overall_pct < 75:
                    st.warning("Your attendance is below 75%.")
                else:
                    st.success("Your attendance is above 75%. Keep it up!")

        with tab_subjects:
            if held.empty:
                st.info("No classes have been held yet.")
            else:
                st.subheader("📚 Attendance by Subject")
                table = summary.rename(columns={
                    "subject": "Subject",
                    "classes_attended": "Attended",
                    "classes_held": "Held",
                    "percentage": "Percentage (%)",
                })[["Subject", "Attended", "Held", "Percentage (%)"]]
                st.dataframe(table, use_container_width=True, hide_index=True)
                st.bar_chart(table.set_index("Subject")[["Percentage (%)"]])

        with tab_calendar:
            if my_attendance.empty:
                st.info("No attendance records yet.")
            else:
                st.subheader("📅 Attendance Calendar")
                calendar_df = my_attendance.copy()
                calendar_df["date"] = pd.to_datetime(calendar_df["date"])
                calendar_df = calendar_df.sort_values("date", ascending=False)
                calendar_df["Day"] = calendar_df["date"].dt.strftime("%A")
                calendar_df["Date"] = calendar_df["date"].dt.strftime("%d %b %Y")
                st.dataframe(
                    calendar_df[["Date", "Day", "subject", "time"]],
                    use_container_width=True, hide_index=True
                )

                st.subheader("📋 Full Attendance Log")
                st.dataframe(my_attendance, use_container_width=True, hide_index=True)

    st.divider()
    st.caption("🎓 SmartAttend — Built for Tech Utsav 2026")