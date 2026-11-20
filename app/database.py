import sqlite3
import os

# Get the main project directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Store database in the main data folder
DATABASE_PATH = os.path.join(
    BASE_DIR, "data", "attendance.db"
)


def get_connection():

    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    return connection


def create_tables():

    connection = get_connection()

    cursor = connection.cursor()

    # Student information
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (

            student_id TEXT PRIMARY KEY,

            full_name TEXT NOT NULL,

            department TEXT,

            year TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    # Face embeddings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS face_embeddings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id TEXT NOT NULL,

            embedding BLOB NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (student_id)
            REFERENCES students(student_id)
            ON DELETE CASCADE

        )
    """)

    # Attendance records
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id TEXT NOT NULL,

            attendance_date TEXT NOT NULL,

            attendance_time TEXT NOT NULL,

            status TEXT DEFAULT 'Present',

            FOREIGN KEY (student_id)
            REFERENCES students(student_id)
            ON DELETE CASCADE,

            UNIQUE(student_id, attendance_date)

        )
    """)

    connection.commit()

    connection.close()

    print("Database initialized successfully!")
    print("Students table created!")
    print("Face embeddings table created!")
    print("Attendance table created!")


if __name__ == "__main__":

    create_tables()
