
import torch
from app.registration import register_student
from app.database import get_connection

# Create a temporary test embedding (512 dimensions)
test_embedding = torch.randn(512)
test_embedding = torch.nn.functional.normalize(
    test_embedding, dim=0
)

# Register a sample student
success, message = register_student(
    student_id="TEST001",
    full_name="Test Student",
    department="Computer Science",
    year="3rd Year",
    embeddings=[test_embedding]
)

print(message)

# Verify the database records
connection = get_connection()
cursor = connection.cursor()

cursor.execute(
    "SELECT * FROM students WHERE student_id = ?",
    ("TEST001",)
)

student = cursor.fetchone()

cursor.execute(
    "SELECT COUNT(*) FROM face_embeddings WHERE student_id = ?",
    ("TEST001",)
)

embedding_count = cursor.fetchone()[0]

print("\nStudent record:", dict(student) if student else None)
print("Stored embeddings:", embedding_count)

connection.close()
