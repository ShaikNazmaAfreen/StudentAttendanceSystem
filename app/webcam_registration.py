
import os
import re
import cv2
from PIL import Image

from app.face_engine import FaceEngine


# Main project directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Student photograph directory
PHOTO_DIR = os.path.join(BASE_DIR, "student_photos")


def capture_student_faces(student_id, number_of_photos=5):

    # Validate student ID before using it as a folder name
    if not re.fullmatch(r"[A-Za-z0-9_-]+", student_id):
        print("Invalid student ID.")
        return None

    student_folder = os.path.join(PHOTO_DIR, student_id)

    if os.path.exists(student_folder) and os.listdir(student_folder):
        print("This student already has photographs.")
        return None

    os.makedirs(student_folder, exist_ok=True)

    # Initialize FaceNet
    engine = FaceEngine()

    # Open webcam
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Unable to access webcam.")
        return None

    embeddings = []
    photo_count = 0

    print("\nStudent face capture started.")
    print("Press S to capture a photograph.")
    print("Press Q to quit.")

    try:

        while photo_count < number_of_photos:

            success, frame = camera.read()

            if not success:
                print("Unable to read webcam frame.")
                break

            display_frame = frame.copy()

            cv2.putText(
                display_frame,
                f"Photos captured: {photo_count}/{number_of_photos}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

            cv2.imshow("Student Face Registration", display_frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("Capture cancelled.")
                break

            if key == ord('s'):

                rgb_frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB
                )

                pil_image = Image.fromarray(rgb_frame)

                embedding = engine.extract_embedding(pil_image)

                if embedding is None:
                    print("No single face detected. Try again.")
                    continue

                photo_count += 1

                photo_path = os.path.join(
                    student_folder,
                    f"photo_{photo_count:02d}.jpg"
                )

                cv2.imwrite(photo_path, frame)

                embeddings.append(embedding)

                print(
                    f"Photo {photo_count}/{number_of_photos} "
                    "captured successfully!"
                )

    finally:

        camera.release()
        cv2.destroyAllWindows()

    if photo_count != number_of_photos:

        print("Registration capture incomplete.")

        # Remove incomplete photographs
        for filename in os.listdir(student_folder):
            os.remove(os.path.join(student_folder, filename))

        if os.path.exists(student_folder):
            os.rmdir(student_folder)

        return None

    print("\nAll photographs captured successfully!")

    return embeddings
