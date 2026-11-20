
import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO

from app.database import get_connection
from app.attendance import finalize_attendance


def show_dashboard():

    st.title("📊 Admin Dashboard")
    st.write("Student Attendance Management")

    connection = get_connection()

    try:
        total_students = pd.read_sql_query(
            "SELECT COUNT(*) AS total FROM students",
            connection
        ).iloc[0]["total"]

        today = date.today().strftime("%Y-%m-%d")

        today_attendance = pd.read_sql_query("""
            SELECT
                s.student_id AS 'Student ID',
                s.full_name AS 'Student Name',
                s.department AS 'Department',
                s.year AS 'Year',
                a.attendance_date AS 'Date',
                a.attendance_time AS 'Time',
                a.status AS 'Status'
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.attendance_date = ?
            ORDER BY a.attendance_time DESC
        """, connection, params=(today,))

        students = pd.read_sql_query("""
            SELECT
                student_id AS 'Student ID',
                full_name AS 'Student Name',
                department AS 'Department',
                year AS 'Year'
            FROM students
            ORDER BY student_id
        """, connection)

        all_attendance = pd.read_sql_query("""
            SELECT
                s.student_id AS 'Student ID',
                s.full_name AS 'Student Name',
                s.department AS 'Department',
                s.year AS 'Year',
                a.attendance_date AS 'Date',
                a.attendance_time AS 'Time',
                a.status AS 'Status'
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            ORDER BY a.attendance_date DESC,
                     a.attendance_time DESC
        """, connection)

    finally:
        connection.close()

    # Today's statistics
    total_present = len(
        today_attendance[today_attendance["Status"] == "Present"]
    )

    total_absent = len(
        today_attendance[today_attendance["Status"] == "Absent"]
    )

    not_finalized = total_students - total_present - total_absent

    st.subheader("Today's Overview")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Students", total_students)
    col2.metric("Present Today", total_present)
    col3.metric("Absent Today", total_absent)

    if not_finalized > 0:
        st.info(
            f"{not_finalized} students have not yet been assigned "
            "an attendance status. Finalize attendance after the session."
        )

    st.divider()

    # Today's attendance
    st.subheader("📅 Today's Attendance")

    if not today_attendance.empty:
        st.dataframe(
            today_attendance,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No attendance has been marked today.")

    st.divider()

    # Student search
    st.subheader("👨‍🎓 Registered Students")

    search_text = st.text_input("Search by Student ID or Name")

    departments = ["All Departments"] + sorted(
        students["Department"].dropna().unique().tolist()
    )

    selected_department = st.selectbox(
        "Filter by Department",
        departments
    )

    filtered_students = students.copy()

    if search_text:
        filtered_students = filtered_students[
            filtered_students["Student ID"].astype(str).str.contains(
                search_text, case=False, na=False
            )
            |
            filtered_students["Student Name"].str.contains(
                search_text, case=False, na=False
            )
        ]

    if selected_department != "All Departments":
        filtered_students = filtered_students[
            filtered_students["Department"] == selected_department
        ]

    st.write("Students found:", len(filtered_students))

    st.dataframe(
        filtered_students,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # Date-wise attendance
    st.subheader("🔎 Date-wise Attendance")

    selected_date = st.date_input(
        "Select Attendance Date",
        value=date.today()
    )

    selected_date_string = selected_date.strftime("%Y-%m-%d")

    st.warning(
        "Finalize attendance only after all students have had "
        "the opportunity to mark their attendance."
    )

    if st.button("Finalize Attendance for Selected Date"):
        success, result = finalize_attendance(selected_date_string)

        if success:
            st.success(
                f"Attendance finalized! {result} students marked Absent."
            )
            st.rerun()
        else:
            st.error(f"Could not finalize attendance: {result}")

    # Reload all records after finalization
    connection = get_connection()

    try:
        date_attendance = pd.read_sql_query("""
    SELECT
        s.student_id AS 'Student ID',
        s.full_name AS 'Student Name',
        s.department AS 'Department',
        s.year AS 'Year',
        a.attendance_date AS 'Date',
        a.attendance_time AS 'Time',
        a.status AS 'Status'
    FROM students s
    LEFT JOIN attendance a
        ON s.student_id = a.student_id
        AND a.attendance_date = ?
    ORDER BY
        CASE
            WHEN a.status = 'Present' THEN 0
            WHEN a.status = 'Absent' THEN 1
            ELSE 2
        END,
        s.student_id
""", connection, params=(selected_date_string,))

    finally:
        connection.close()

    # Display selected date's records
    st.write(
        "Present students:",
        len(date_attendance[date_attendance["Status"] == "Present"])
    )

    st.write(
        "Absent students:",
        len(date_attendance[date_attendance["Status"] == "Absent"])
    )

    st.dataframe(
        date_attendance,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # Excel downloads
    st.subheader("📥 Download Attendance Reports")

    if not all_attendance.empty:

        full_buffer = BytesIO()

        with pd.ExcelWriter(full_buffer, engine="openpyxl") as writer:
            all_attendance.to_excel(
                writer,
                index=False,
                sheet_name="Attendance"
            )

        st.download_button(
            label="Download Full Attendance Report (Excel)",
            data=full_buffer.getvalue(),
            file_name="Student_Attendance_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.info("No attendance records available for export.")

    # Selected-date report includes every registered student
    date_buffer = BytesIO()

    with pd.ExcelWriter(date_buffer, engine="openpyxl") as writer:
        date_attendance.to_excel(
            writer,
            index=False,
            sheet_name="Daily Attendance"
        )

    st.download_button(
        label="Download Selected Date Report (Excel)",
        data=date_buffer.getvalue(),
        file_name=f"Attendance_{selected_date_string}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
