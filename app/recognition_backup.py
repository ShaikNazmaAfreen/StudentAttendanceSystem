
import numpy as np
import torch
import torch.nn.functional as F

from app.database import get_connection


def load_student_profiles():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            s.student_id,
            s.full_name,
            fe.embedding
        FROM students s
        JOIN face_embeddings fe
        ON s.student_id = fe.student_id
        ORDER BY s.student_id
    """)

    rows = cursor.fetchall()
    connection.close()

    profiles = {}

    for row in rows:

        student_id = row["student_id"]
        full_name = row["full_name"]

        embedding_array = np.frombuffer(
            row["embedding"],
            dtype=np.float32
        ).copy()

        if embedding_array.shape[0] != 512:
            continue

        if student_id not in profiles:
            profiles[student_id] = {
                "name": full_name,
                "embeddings": []
            }

        profiles[student_id]["embeddings"].append(
            torch.from_numpy(embedding_array)
        )

    # Calculate one representative profile per student
    for student_id in profiles:

        embeddings = torch.stack(
            profiles[student_id]["embeddings"]
        )

        centroid = embeddings.mean(dim=0)

        centroid = F.normalize(
            centroid.unsqueeze(0),
            p=2,
            dim=1
        ).squeeze(0)

        profiles[student_id]["centroid"] = centroid

    return profiles


def find_best_match(face_embedding):

    profiles = load_student_profiles()

    if not profiles:
        return None

    best_match = None
    highest_similarity = -1.0

    for student_id, profile in profiles.items():

        centroid = profile["centroid"]

        similarity = torch.dot(
            face_embedding,
            centroid
        ).item()

        if similarity > highest_similarity:

            highest_similarity = similarity

            best_match = {
                "student_id": student_id,
                "name": profile["name"],
                "similarity": highest_similarity
            }

    return best_match
