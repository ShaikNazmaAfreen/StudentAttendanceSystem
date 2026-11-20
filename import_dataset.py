
import argparse
import hashlib
import sqlite3
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from openpyxl import load_workbook

from app.face_engine import FaceEngine
from app.database import get_connection


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "FaceRecognition_Dataset"
EXCEL_FILE = ROOT / "student_details.xlsx"


def read_student_mapping():
    workbook = load_workbook(
        EXCEL_FILE, data_only=True, read_only=True
    )
    sheet = workbook.active

    headers = [str(cell.value).strip() for cell in sheet[1]]
    required = [
        "Folder name", "Student ID", "Full name",
        "Department", "Year"
    ]

    if headers != required:
        workbook.close()
        raise ValueError(f"Unexpected Excel headings: {headers}")

    mapping = {}

    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not any(value is not None for value in row):
            continue

        folder, student_id, name, department, year = row

        record = {
            "folder": str(folder).strip(),
            "student_id": str(student_id).strip(),
            "name": str(name).strip(),
            "department": str(department).strip(),
            "year": str(year).strip()
        }

        if not all(record.values()):
            workbook.close()
            raise ValueError(f"Incomplete Excel row: {row}")

        if record["student_id"] in mapping:
            workbook.close()
            raise ValueError(
                f"Duplicate student ID: {record['student_id']}"
            )

        mapping[record["student_id"]] = record

    workbook.close()
    return mapping


def image_hash(image_path):
    digest = hashlib.sha256()

    with open(image_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main(commit=False):
    mapping = read_student_mapping()

    if len(mapping) != 20:
        raise ValueError(
            f"Expected 20 students, found {len(mapping)}"
        )

    print("Loading FaceNet...")
    engine = FaceEngine()

    prepared = []
    seen_hashes = set()

    # Validate and extract embeddings before database changes.
    for student_id, record in mapping.items():

        folder = DATASET / record["folder"]

        if not folder.is_dir():
            raise FileNotFoundError(folder)

        images = sorted(
            path for path in folder.iterdir()
            if path.suffix.lower() in
            [".jpg", ".jpeg", ".png"]
        )

        if len(images) != 10:
            raise ValueError(
                f"{record['folder']} has {len(images)} images, "
                "not 10."
            )

        student_embeddings = []

        for image_path in images:

            digest = image_hash(image_path)

            if digest in seen_hashes:
                raise ValueError(
                    f"Duplicate image detected: {image_path}"
                )

            seen_hashes.add(digest)

            with Image.open(image_path) as source:
                image = ImageOps.exif_transpose(
                    source
                ).convert("RGB")

            embedding = engine.extract_embedding(image)

            if embedding is None:
                raise ValueError(
                    f"Face detection failed: {image_path}"
                )

            if embedding.shape != (512,):
                raise ValueError(
                    f"Unexpected embedding shape: {image_path}"
                )

            if not torch.isfinite(embedding).all():
                raise ValueError(
                    f"Invalid embedding values: {image_path}"
                )

            student_embeddings.append(
                (image_path, digest, embedding.cpu().numpy())
            )

        prepared.append((record, student_embeddings))

        print(
            record["student_id"],
            record["name"],
            "- 10 embeddings ready"
        )

    print("\nAll 200 photographs passed validation.")

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Check existing student records.
        for record, _ in prepared:
            existing = cursor.execute(
                "SELECT * FROM students WHERE student_id=?",
                (record["student_id"],)
            ).fetchone()

            if existing:
                matches = (
                    existing["full_name"].strip().casefold()
                    == record["name"].casefold()
                    and existing["department"].strip().casefold()
                    == record["department"].casefold()
                    and str(existing["year"]).strip()
                    == record["year"]
                )

                if not matches:
                    raise ValueError(
                        "Existing student details do not match "
                        f"Excel for ID {record['student_id']}"
                    )

        # This table makes imports safe to rerun.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS face_imports (
                image_hash TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                image_path TEXT NOT NULL,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        already_imported = {
            row["image_hash"]
            for row in cursor.execute(
                "SELECT image_hash FROM face_imports"
            ).fetchall()
        }

        new_count = sum(
            digest not in already_imported
            for _, images in prepared
            for _, digest, _ in images
        )

        print("Already imported images:", len(already_imported))
        print("New embeddings to import:", new_count)

        if not commit:
            connection.rollback()
            print("\nDRY RUN SUCCESSFUL.")
            print("Database records were not changed.")
            print("To perform the import, use:")
            print("python import_dataset.py --commit")
            return

        # Actual import: all changes are one transaction.
        for record, images in prepared:

            cursor.execute("""
                INSERT OR IGNORE INTO students
                (student_id, full_name, department, year)
                VALUES (?, ?, ?, ?)
            """, (
                record["student_id"],
                record["name"],
                record["department"],
                record["year"]
            ))

            for image_path, digest, embedding in images:

                if digest in already_imported:
                    continue

                embedding_bytes = sqlite3.Binary(
                    np.asarray(
                        embedding, dtype=np.float32
                    ).tobytes()
                )

                cursor.execute("""
                    INSERT INTO face_embeddings
                    (student_id, embedding)
                    VALUES (?, ?)
                """, (
                    record["student_id"],
                    embedding_bytes
                ))

                cursor.execute("""
                    INSERT INTO face_imports
                    (image_hash, student_id, image_path)
                    VALUES (?, ?, ?)
                """, (
                    digest,
                    record["student_id"],
                    str(image_path.relative_to(ROOT))
                ))

                already_imported.add(digest)

        connection.commit()

        print("\nIMPORT COMPLETED SUCCESSFULLY!")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Perform the database import"
    )
    args = parser.parse_args()

    main(commit=args.commit)
