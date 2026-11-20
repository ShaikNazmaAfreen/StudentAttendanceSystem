
from datetime import datetime
import sqlite3

from app.database import get_connection


def mark_attendance(student_id):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Check whether the student is registered.
        cursor.execute(
            "SELECT student_id FROM students WHERE student_id = ?",
            (student_id,)
        )

        student = cursor.fetchone()

        if student is None:
            return False, "Student is not registered."

        now = datetime.now()

        attendance_date = now.strftime("%Y-%m-%d")
        attendance_time = now.strftime("%H:%M:%S")

        # Check today's existing attendance record.
        cursor.execute("""
            SELECT id, status
            FROM attendance
            WHERE student_id = ?
            AND attendance_date = ?
        """, (student_id, attendance_date))

        existing = cursor.fetchone()

        if existing:

            # Already Present: prevent duplicate attendance.
            if existing["status"] == "Present":
                return False, "Attendance already marked today."

            # Previously Absent: update to Present.
            if existing["status"] == "Absent":

                cursor.execute("""
                    UPDATE attendance
                    SET status = 'Present',
                        attendance_time = ?
                    WHERE id = ?
                """, (attendance_time, existing["id"]))

                connection.commit()

                return True, "Absent status updated to Present successfully!"

        # No existing record: insert new attendance.
        cursor.execute("""
            INSERT INTO attendance
            (student_id, attendance_date, attendance_time, status)
            VALUES (?, ?, ?, 'Present')
        """, (student_id, attendance_date, attendance_time))

        connection.commit()

        return True, "Attendance marked successfully!"

    except sqlite3.IntegrityError:

        connection.rollback()

        return False, "Attendance already marked today."

    except Exception as error:

        connection.rollback()

        return False, f"Error: {error}"

    finally:
        connection.close()


def finalize_attendance(attendance_date):
    """
    Mark students who have not recorded attendance
    on the selected date as Absent.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO attendance
            (student_id, attendance_date, attendance_time, status)

            SELECT
                s.student_id,
                ?,
                'N/A',
                'Absent'

            FROM students s

            WHERE NOT EXISTS (
                SELECT 1
                FROM attendance a

                WHERE a.student_id = s.student_id
                AND a.attendance_date = ?
            )

        """, (attendance_date, attendance_date))

        absent_count = cursor.rowcount

        connection.commit()

        return True, absent_count

    except Exception as error:

        connection.rollback()

        return False, str(error)

    finally:
        connection.close()
