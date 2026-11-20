
import os
import shutil

from app.database import get_connection
from app.registration import register_student
from app.webcam_registration import capture_student_faces


def main():

    print("\n===== STUDENT REGISTRATION =====\n")

    # Collect student details
    student_id = input("Enter Student ID: ").strip()
    full_name = input("Enter Full Name: ").strip()
    department = input("Enter Department: ").strip()
    year = input("Enter Academic Year: ").strip()

    if not all([student_id, full_name, department, year]):
        print("All fields are required.")
        return

    # Check whether student ID already exists
    connection = get_connection()

    existing = connection.execute(
        "SELECT student_id FROM students WHERE student_id = ?",
        (student_id,)
    ).fetchone()

    connection.close()

    if existing:
        print("This Student ID is already registered.")
        return

    # Obtain consent
    consent = input(
        "\nHas the student given consent for face-data collection? (yes/no): "
    ).strip().lower()

    if consent != "yes":
        print("Registration cancelled. Consent is required.")
        return

    print("\nPreparing webcam registration...")
    print("You will capture 5 photographs.")
    print("Press S to capture each photograph.")
    print("Change your head angle slightly between captures.")
    print("Press Q to cancel.")

    # Capture photographs and generate embeddings
    embeddings = capture_student_faces(
        student_id,
        number_of_photos=5
    )

    if embeddings is None:
        print("Registration cancelled or capture incomplete.")
        return

    # Save student details and embeddings
    success, message = register_student(
        student_id,
        full_name,
        department,
        year,
        embeddings
    )

    print("\n" + message)

    if not success:

        # Remove photographs if database registration failed
        project_dir = os.path.dirname(os.path.abspath(__file__))
        photo_folder = os.path.join(
            project_dir, "student_photos", student_id
        )

        if os.path.exists(photo_folder):
            shutil.rmtree(photo_folder)

        return

    print("\nStudent registration completed!")
    print("Student ID:", student_id)
    print("Photographs captured:", len(embeddings))
    print("Face embeddings stored:", len(embeddings))


if __name__ == "__main__":
    main()
