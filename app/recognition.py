
import numpy as np
import torch
import torch.nn.functional as F

from app.database import get_connection


def load_department_profiles():
    """
    Load registered student embeddings and organize
    students department-wise.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                s.student_id,
                s.full_name,
                s.department,
                fe.embedding
            FROM students s
            JOIN face_embeddings fe
                ON s.student_id = fe.student_id
            ORDER BY s.department, s.student_id
        """)

        rows = cursor.fetchall()

    finally:
        connection.close()

    departments = {}

    for row in rows:

        student_id = row["student_id"]
        full_name = row["full_name"]
        department = row["department"].strip().upper()

        embedding_array = np.frombuffer(
            row["embedding"],
            dtype=np.float32
        ).copy()

        if embedding_array.shape[0] != 512:
            continue

        embedding = torch.from_numpy(embedding_array)

        if department not in departments:
            departments[department] = {}

        if student_id not in departments[department]:
            departments[department][student_id] = {
                "name": full_name,
                "embeddings": []
            }

        departments[department][student_id]["embeddings"].append(
            embedding
        )

    # Calculate one reference centroid for each student.
    for department in departments:

        for student_id in departments[department]:

            embeddings = torch.stack(
                departments[department][student_id]["embeddings"]
            )

            centroid = embeddings.mean(dim=0)

            centroid = F.normalize(
                centroid.unsqueeze(0),
                p=2,
                dim=1
            ).squeeze(0)

            departments[department][student_id]["centroid"] = centroid

    return departments


def find_best_match(face_embedding):
    """
    Hierarchical recognition:

    Stage 1: Find the best student in every department.
    Stage 2: Compare department winners and select
             the overall best student.
    """

    departments = load_department_profiles()

    if not departments:
        return None

    face_embedding = face_embedding.detach().cpu().float()

    face_embedding = F.normalize(
        face_embedding.unsqueeze(0),
        p=2,
        dim=1
    ).squeeze(0)

    department_winners = []

    # STAGE 1: Search each department.
    print("\nSTAGE 1: DEPARTMENT-WISE SEARCH")

    for department, students in departments.items():

        best_student = None
        highest_similarity = -1.0

        for student_id, profile in students.items():

            centroid = profile["centroid"]

            similarity = torch.dot(
                face_embedding,
                centroid
            ).item()

            if similarity > highest_similarity:

                highest_similarity = similarity

                best_student = {
                    "student_id": student_id,
                    "name": profile["name"],
                    "department": department,
                    "similarity": similarity
                }

        if best_student is not None:

            department_winners.append(best_student)

            print(
                f"{department}: "
                f"{best_student['name']} "
                f"({best_student['similarity']:.4f})"
            )

    # STAGE 2: Compare the department winners.
    if not department_winners:
        return None

    print("\nSTAGE 2: FINAL COMPARISON")

    final_match = max(
        department_winners,
        key=lambda candidate: candidate["similarity"]
    )

    print(
        "Best overall match:",
        final_match["name"],
        "| Department:",
        final_match["department"],
        "| Similarity:",
        f"{final_match['similarity']:.4f}"
    )

        # UNKNOWN PERSON REJECTION
    # Provisional threshold based on your webcam tests.
    SIMILARITY_THRESHOLD = 0.80

    if final_match["similarity"] < SIMILARITY_THRESHOLD:
        print("\nUNKNOWN PERSON DETECTED!")
        print("Best similarity:", round(final_match["similarity"], 4))
        print("Required similarity:", SIMILARITY_THRESHOLD)
        return None

    print("\nREGISTERED STUDENT RECOGNIZED!")
    return final_match
