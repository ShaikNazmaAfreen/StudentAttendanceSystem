
import cv2
from PIL import Image

from app.face_engine import FaceEngine
from app.recognition import find_best_match

print("Initializing Face Recognition Engine...")

engine = FaceEngine()

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Unable to access webcam.")
    exit()

print("\nWebcam opened successfully!")
print("Show the face of registered student 1001.")
print("Press S to capture.")
print("Press Q to quit.")

captured_frame = None

while True:

    success, frame = camera.read()

    if not success:
        print("Unable to read webcam.")
        break

    cv2.imshow("Live Face Recognition Test", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('s'):
        captured_frame = frame.copy()
        break

    elif key == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()

if captured_frame is not None:

    rgb_frame = cv2.cvtColor(
        captured_frame,
        cv2.COLOR_BGR2RGB
    )

    pil_image = Image.fromarray(rgb_frame)

    print("\nExtracting face embedding...")

    embedding = engine.extract_embedding(pil_image)

    if embedding is None:

        print("No single face detected.")

    else:

        print("Face embedding generated successfully!")

        print("\nComparing with registered students...")

        result = find_best_match(embedding)

        if result is not None:

            print("\nBest matching student:")
            print("Student ID:", result["student_id"])
            print("Name:", result["name"])
            print(
                "Cosine similarity:",
                round(result["similarity"], 4)
            )

        else:

            print("\nUNKNOWN PERSON!")
            print("Identity could not be verified.")
            print("Attendance NOT marked.")

else:

    print("No photograph captured.")
