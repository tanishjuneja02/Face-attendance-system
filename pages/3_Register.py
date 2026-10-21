"""Admin: register students (with face), deactivate/restore/delete them, manage subjects and staff."""
import io

import streamlit as st

from core import auth, database, face, photos, ui

ui.setup("Register", "🧑‍🎓")
ui.require_staff(roles=("admin",))

st.title(":material/school: Register & Manage")
if "flash" in st.session_state:  # message saved before a rerun
    st.success(st.session_state.pop("flash"))
tab_students, tab_subjects, tab_staff = st.tabs(["Students", "Subjects", "Staff accounts"])

def _reject_if_face_exists(embedding, exclude_id=None):
    """Raise DuplicateError if this face already belongs to a registered student (active or deactivated)."""
    everyone = database.get_students_with_embeddings(include_deleted=True)
    hit = face.find_duplicate(embedding, everyone, exclude_id=exclude_id)
    if hit is None:
        return
    owner = database.get_student(hit.student_id)
    who = f"{owner['name']} (roll {owner['roll_no']}, {owner['class_name']})"
    if owner["is_deleted"]:
        raise database.DuplicateError(
            f"This face is already registered to {who}, who is deactivated. "
            "Restore them from 'Recently deleted' instead of registering again.")
    raise database.DuplicateError(f"This face is already registered to {who}.")


# ------------------------------------------------------------------ students
with tab_students:
    st.subheader("Register a new student")
    # Upload is the default. The camera only opens if you choose it.
    method = st.radio("Face photo", ["Upload a photo", "Use camera"], horizontal=True)

    with st.form("add_student", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        roll_no = c1.text_input("Roll number")
        name = c2.text_input("Full name")
        class_name = c3.text_input("Class (e.g. CS-3A)")
        if method == "Upload a photo":
            image_file = st.file_uploader("Upload a clear, front-facing photo", type=["jpg", "jpeg", "png"])
        else:
            image_file = st.camera_input("Take a clear, front-facing photo")
        submitted = st.form_submit_button("Register student")

    if submitted:
        if not (roll_no.strip() and name.strip() and class_name.strip()):
            st.warning("Please fill roll number, name and class.")
        elif image_file is None:
            st.warning("Please provide a face photo.")
        else:
            try:
                existing = database.get_student_by_roll(roll_no)
                if existing and existing["is_deleted"]:
                    raise database.DuplicateError(
                        f"Roll number '{roll_no.strip()}' belongs to a deactivated student. "
                        "Restore them from 'Recently deleted' below."
                    )
                if existing:
                    raise database.DuplicateError(f"Roll number '{roll_no.strip()}' already exists.")
                with st.spinner("Reading face..."):
                    image = ui.read_image(image_file)
                    embedding = face.get_registration_embeddings(image)
                _reject_if_face_exists(embedding)
                path = photos.save_photo(roll_no, image)
                database.add_student(roll_no, name, class_name, photo_path=path, embedding=embedding)
                st.success(f"Registered {name.strip()} (roll {roll_no.strip()}).")
            except (face.FaceNotFoundError, database.DuplicateError, ValueError) as exc:
                st.error(str(exc))

    # ---- active students: deactivate (soft delete)
    st.divider()
    st.subheader("Registered students")
    students = database.list_students()

    legacy = [s for s in database.get_students_with_embeddings() if face.is_legacy_embedding(s["embedding"])]
    if legacy:
        st.warning(
            f"{len(legacy)} student(s) were registered with the old face format. "
            "Rebuild their face data once so they match on any camera."
        )
        if st.button(":material/refresh: Rebuild face data from saved photos", key="rebuild_faces"):
            done, failed = 0, []
            with st.spinner("Rebuilding face data... this takes a few seconds per student."):
                for s in database.get_students_with_embeddings():
                    try:
                        photo_bytes = photos.read_photo_bytes(s["photo_path"])
                        if photo_bytes is None:
                            raise face.FaceNotFoundError("saved photo is missing")
                        image = ui.read_image(io.BytesIO(photo_bytes))
                        database.update_student(s["id"], s["roll_no"], s["name"], s["class_name"],
                                                embedding=face.get_registration_embeddings(image))
                        done += 1
                    except (face.FaceNotFoundError, OSError) as exc:
                        failed.append(f"{s['roll_no']} ({exc})")
            st.session_state["flash"] = f"Rebuilt {done} student(s)." + (
                f" Re-register these with a new photo: {', '.join(failed)}." if failed else "")
            st.rerun()

    if students:
        st.dataframe(
            [{"Roll No": s["roll_no"], "Name": s["name"], "Class": s["class_name"]} for s in students],
            use_container_width=True, hide_index=True,
        )
        labels = {s["id"]: f"{s['roll_no']} - {s['name']} ({s['class_name']})" for s in students}

        with st.expander(":material/edit: Edit a student"):
            edit_id = st.selectbox("Select a student to edit", list(labels),
                                   format_func=labels.get, key="edit_student_select")
            cur = next(s for s in students if s["id"] == edit_id)
            with st.form("edit_student"):
                c1, c2, c3 = st.columns(3)
                new_roll = c1.text_input("Roll number", value=cur["roll_no"], key=f"edit_roll_{edit_id}")
                new_name = c2.text_input("Full name", value=cur["name"], key=f"edit_name_{edit_id}")
                new_class = c3.text_input("Class", value=cur["class_name"], key=f"edit_class_{edit_id}")
                new_image = st.file_uploader("Replace face photo (optional)", type=["jpg", "jpeg", "png"],
                                             key=f"edit_photo_{edit_id}")
                save_student = st.form_submit_button("Save changes")
            if save_student:
                if not (new_roll.strip() and new_name.strip() and new_class.strip()):
                    st.warning("Roll number, name and class cannot be empty.")
                else:
                    try:
                        other = database.get_student_by_roll(new_roll)
                        if other and other["id"] != edit_id:
                            raise database.DuplicateError(
                                f"Roll number '{new_roll.strip()}' is already used by another student.")
                        photo_path, embedding = None, None
                        if new_image is not None:
                            with st.spinner("Reading face..."):
                                image = ui.read_image(new_image)
                                embedding = face.get_registration_embeddings(image)
                            _reject_if_face_exists(embedding, exclude_id=edit_id)
                            photo_path = photos.save_photo(new_roll, image)
                        elif new_roll.strip() != cur["roll_no"] and cur["photo_path"]:
                            photo_path = photos.rename_photo(cur["photo_path"], new_roll)
                        database.update_student(edit_id, new_roll, new_name, new_class,
                                                photo_path=photo_path, embedding=embedding)
                        if new_image is not None and cur["photo_path"] and cur["photo_path"] != photo_path:
                            photos.delete_photo(cur["photo_path"])
                        st.session_state["flash"] = f"Updated {new_name.strip()}."
                        st.rerun()
                    except (face.FaceNotFoundError, database.DuplicateError, ValueError) as exc:
                        st.error(str(exc))

        chosen = st.selectbox("Select a student to deactivate", list(labels),
                              format_func=labels.get, key="deactivate_select")
        st.caption("Deactivating hides the student and stops face matching for them. "
                   "Their past attendance is kept, and you can restore them later.")
        confirm = st.checkbox("Yes, deactivate this student", key="deactivate_confirm")
        if st.button(":material/block: Deactivate student", disabled=not confirm, key="deactivate_btn"):
            database.deactivate_student(chosen)
            st.success("Student deactivated. You can restore them under 'Recently deleted'.")
            st.rerun()
    else:
        st.info("No active students.")

    # ---- deactivated students: restore or delete permanently
    st.divider()
    st.subheader(":material/restore: Recently deleted (deactivated)")
    deleted = database.list_students(deleted=True)
    if not deleted:
        st.caption("No deactivated students.")
    else:
        st.dataframe(
            [{"Roll No": s["roll_no"], "Name": s["name"], "Class": s["class_name"]} for s in deleted],
            use_container_width=True, hide_index=True,
        )
        del_labels = {s["id"]: f"{s['roll_no']} - {s['name']} ({s['class_name']})" for s in deleted}
        picked = st.selectbox("Select a deactivated student", list(del_labels),
                              format_func=del_labels.get, key="restore_select")
        picked_student = next(s for s in deleted if s["id"] == picked)

        col_restore, col_perm = st.columns(2)
        with col_restore:
            if st.button(":material/restore: Restore this student", key="restore_btn"):
                database.restore_student(picked)
                st.success("Student restored.")
                st.rerun()
        with col_perm:
            st.caption(":material/warning: Permanent delete removes the student, their photo and ALL their attendance. "
                       "This cannot be undone.")
            confirm_perm = st.checkbox("Yes, delete permanently", key="perm_confirm")
            if st.button(":material/delete_forever: Delete permanently", disabled=not confirm_perm, key="perm_btn"):
                database.delete_student(picked)
                photos.delete_photo(picked_student["photo_path"])
                st.success("Student permanently deleted.")
                st.rerun()

# ------------------------------------------------------------------ subjects
with tab_subjects:
    with st.form("add_subject", clear_on_submit=True):
        subject_name = st.text_input("New subject name")
        if st.form_submit_button("Add subject"):
            try:
                database.add_subject(subject_name)
                st.success("Subject added.")
            except (ValueError, database.DuplicateError) as exc:
                st.error(str(exc))
    subjects = database.list_subjects()
    st.write("**Current subjects:** " + ", ".join(s["name"] for s in subjects))

    if subjects:
        st.divider()
        st.subheader("Rename or delete a subject")
        sub_labels = {s["id"]: s["name"] for s in subjects}
        sub_id = st.selectbox("Select a subject", list(sub_labels),
                              format_func=sub_labels.get, key="subject_select")
        with st.form("rename_subject"):
            new_subject = st.text_input("New name", value=sub_labels[sub_id], key=f"subject_name_{sub_id}")
            if st.form_submit_button("Save name"):
                try:
                    database.update_subject(sub_id, new_subject)
                    st.session_state["flash"] = f"Subject renamed to '{new_subject.strip()}'."
                    st.rerun()
                except (ValueError, database.DuplicateError) as exc:
                    st.error(str(exc))
        st.caption(":material/warning: Deleting a subject also deletes ALL attendance recorded for it. "
                   "This cannot be undone.")
        confirm_sub = st.checkbox("Yes, delete this subject and its attendance", key="subject_del_confirm")
        if st.button(":material/delete_forever: Delete subject", disabled=not confirm_sub, key="subject_del_btn"):
            database.delete_subject(sub_id)
            st.session_state["flash"] = "Subject deleted."
            st.rerun()

# --------------------------------------------------------------------- staff
with tab_staff:
    with st.form("add_staff", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        new_user = c1.text_input("Username")
        new_pass = c2.text_input("Password (min 6 characters)", type="password")
        new_role = c3.selectbox("Role", list(auth.ROLES))
        if st.form_submit_button("Create account"):
            try:
                auth.create_staff(new_user, new_pass, new_role)
                st.success(f"Created {new_role} account '{new_user.strip()}'.")
            except (ValueError, database.DuplicateError) as exc:
                st.error(str(exc))
    staff_list = database.list_staff()
    st.dataframe(staff_list, use_container_width=True, hide_index=True)

    me = ui.current_staff()
    if staff_list:
        st.divider()
        st.subheader("Edit or delete an account")
        staff_labels = {s["id"]: f"{s['username']} ({s['role']})" for s in staff_list}
        staff_id = st.selectbox("Select an account", list(staff_labels),
                                format_func=staff_labels.get, key="staff_select")
        acct = next(s for s in staff_list if s["id"] == staff_id)
        is_me = staff_id == me["id"]
        roles = list(auth.ROLES)
        with st.form("edit_staff"):
            c1, c2 = st.columns(2)
            edit_user = c1.text_input("Username", value=acct["username"], key=f"staff_user_{staff_id}")
            edit_role = c2.selectbox("Role", roles, index=roles.index(acct["role"]),
                                     disabled=is_me, key=f"staff_role_{staff_id}")
            edit_pass = st.text_input("New password (leave blank to keep the current one)",
                                      type="password", key=f"staff_pass_{staff_id}")
            if st.form_submit_button("Save account"):
                try:
                    auth.update_staff(staff_id, edit_user, edit_role, edit_pass or None)
                    if is_me:  # keep the logged-in session in step with the new username
                        st.session_state["staff"] = {**me, "username": edit_user.strip()}
                    st.session_state["flash"] = f"Updated account '{edit_user.strip()}'."
                    st.rerun()
                except (ValueError, database.DuplicateError) as exc:
                    st.error(str(exc))
        if is_me:
            st.caption("You are logged in as this account, so its role can't be changed and it can't be deleted here.")
        else:
            confirm_acct = st.checkbox("Yes, delete this account", key="staff_del_confirm")
            if st.button(":material/delete_forever: Delete account", disabled=not confirm_acct, key="staff_del_btn"):
                try:
                    auth.delete_staff(staff_id)
                    st.session_state["flash"] = "Account deleted."
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))