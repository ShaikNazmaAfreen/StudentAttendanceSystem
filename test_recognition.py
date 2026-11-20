
from app.recognition import load_student_profiles

profiles = load_student_profiles()

print("Registered students:", len(profiles))

for student_id, profile in profiles.items():

    print("\nStudent ID:", student_id)
    print("Name:", profile["name"])
    print("Number of embeddings:", len(profile["embeddings"]))
    print("Centroid shape:", profile["centroid"].shape)

print("\nStudent profiles loaded successfully!")
