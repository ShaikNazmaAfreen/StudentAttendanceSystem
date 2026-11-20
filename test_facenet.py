
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1

# Use CPU because your laptop does not have CUDA
device = torch.device("cpu")

print("Loading saved FaceNet weights...")

# Load the FaceNet weights copied from Google Colab
weights_data = torch.load(
    "models/facenet_vggface2_weights.pt",
    map_location=device,
    weights_only=False
)

# Create the FaceNet architecture and load your saved weights
facenet = InceptionResnetV1(pretrained=None).eval()
load_result = facenet.load_state_dict(
    weights_data["model_state_dict"],
    strict=False
)

print("Missing keys:", load_result.missing_keys)
print("Unexpected keys:", load_result.unexpected_keys)

print("FaceNet model loaded successfully!")

# Load the reference profiles
print("\nLoading reference profiles...")

profiles = torch.load(
    "models/facenet_reference_profiles.pt",
    map_location=device,
    weights_only=False
)

reference_centroids = profiles["reference_centroids"]
class_names = profiles["class_names"]
class_to_idx = profiles["class_to_idx"]

print("Reference profiles loaded successfully!")
print("Number of registered identities:", len(class_names))
print("Reference centroid shape:", reference_centroids.shape)

# Initialize the MTCNN face detector
print("\nInitializing MTCNN face detector...")

mtcnn = MTCNN(
    image_size=160,
    margin=20,
    min_face_size=20,
    thresholds=[0.6, 0.7, 0.7],
    factor=0.709,
    post_process=True,
    device=device
)

print("MTCNN initialized successfully!")

print("\nAll FaceNet components loaded successfully!")
