
import torch
import torch.nn.functional as F
from facenet_pytorch import MTCNN, InceptionResnetV1


class FaceEngine:

    def __init__(self):

        self.device = torch.device("cpu")

        print("Loading FaceNet model...")

        weights_data = torch.load(
            "models/facenet_vggface2_weights.pt",
            map_location=self.device,
            weights_only=False
        )

        self.model = InceptionResnetV1(
            pretrained=None
        ).eval()

        self.model.load_state_dict(
            weights_data["model_state_dict"],
            strict=False
        )

        print("FaceNet loaded!")

        print("Initializing face detector...")

        self.mtcnn = MTCNN(
            image_size=160,
            margin=30,
            min_face_size=15,
            thresholds=[0.5, 0.6, 0.6],
            factor=0.709,
            post_process=True,
            keep_all=True,
            device=self.device
        )

        print("MTCNN initialized!")

    def extract_embedding(self, image):

        # Detect all faces
        boxes, probabilities = self.mtcnn.detect(image)

        if boxes is None or len(boxes) == 0:
            return None

        # Calculate the area of each detected face
        areas = []

        for box in boxes:
            width = max(0, box[2] - box[0])
            height = max(0, box[3] - box[1])
            areas.append(width * height)

        # Select the largest face
        largest_index = int(torch.tensor(areas).argmax())
        largest_area = areas[largest_index]

        if largest_area <= 0:
            return None

        # Reject if another face is similarly large
        for i, area in enumerate(areas):
            if i != largest_index and area >= 0.5 * largest_area:
                return None

        # Extract the selected face
        selected_box = boxes[largest_index:largest_index + 1]

        faces = self.mtcnn.extract(
            image,
            selected_box,
            None
        )

        if faces is None:
            return None

        # Generate the 512-dimensional FaceNet embedding
        with torch.no_grad():
            embedding = self.model(faces)
            embedding = F.normalize(
                embedding,
                p=2,
                dim=1
            )

        return embedding.squeeze(0)
