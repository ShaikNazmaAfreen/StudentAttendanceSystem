
import sqlite3
import numpy as np

from app.database import get_connection


def register_student(student_id, full_name, department, year, embeddings):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Save student details
        cursor.execute(
            """
            INSERT INTO students
            (student_id, full_name, department, year)
            VALUES (?, ?, ?, ?)
            """,
            (student_id, full_name, department, year)
        )

        # Save each face embedding
        for embedding in embeddings:

            embedding_array = (
                embedding.detach()
                .cpu()
                .numpy()
                .astype(np.float32)
            )

            embedding_bytes = sqlite3.Binary(
                embedding_array.tobytes()
            )

            cursor.execute(
                """
                INSERT INTO face_embeddings
                (student_id, embedding)
                VALUES (?, ?)
                """,
                (student_id, embedding_bytes)
            )

        connection.commit()

        return True, "Student registered successfully!"

    except sqlite3.IntegrityError:

        connection.rollback()

        return False, "This student ID is already registered."

    except Exception as error:

        connection.rollback()

        return False, f"Registration failed: {error}"

    finally:

        connection.close()
