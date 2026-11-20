
import cv2
import torch
from PIL import Image
from app.face_engine import FaceEngine

print("Initializing Face Recognition Engine...")

engine = FaceEngine()

print("\nOpening webcam...")

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Error: Could not access webcam.")
    exit()

print("Webcam opened successfully!")
print("Position your face in front of the camera.")
print("Press S to capture your face.")
print("Press Q to quit.")

captured_frame = None

while True:

    success, frame = camera.read()

    if not success:
        print("Could not read webcam frame.")
        break

    cv2.imshow("FaceNet Test - Press S to Capture", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('s'):
        captured_frame = frame.copy()
        break

    elif key == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()

if captured_frame is not None:

    print("\nProcessing captured face...")

    rgb_image = cv2.cvtColor(
        captured_frame,
        cv2.COLOR_BGR2RGB
    )

    pil_image = Image.fromarray(rgb_image)

    embedding = engine.extract_embedding(pil_image)

    if embedding is not None:

        print("\nFace detected successfully!")

        print("Embedding shape:", embedding.shape)

        print(
            "Embedding dimension:",
            embedding.shape[0]
        )

        print(
            "Embedding vector norm:",
            torch.norm(embedding).item()
        )

        print("\nFaceNet test completed successfully!")

    else:

        print("\nNo single face detected.")
        print("Try again with one clear face.")

else:
    print("\nNo photograph captured.")
