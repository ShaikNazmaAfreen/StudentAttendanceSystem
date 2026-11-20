import os
import base64
import binascii
import re

from datetime import date
from functools import wraps
from io import BytesIO

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError
from werkzeug.security import check_password_hash

from app.database import get_connection
from app.face_engine import FaceEngine
from app.recognition import find_best_match
from app.attendance import mark_attendance


# Load environment variables
load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("SECRET_KEY is missing from the .env file.")

CORS(app, supports_credentials=True)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False
)


# Admin credentials
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")


# Login protection decorator
def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get("admin_logged_in"):
            return jsonify({
                "success": False,
                "message": "Please log in as administrator."
            }), 401

        return function(*args, **kwargs)

    return wrapper


# Admin login API
@app.route("/api/login", methods=["POST"])
def admin_login():

    data = request.get_json(silent=True) or {}

    username = data.get("username", "")
    password = data.get("password", "")

    if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
        return jsonify({
            "success": False,
            "message": "Admin credentials are not configured."
        }), 500

    if (
        username != ADMIN_USERNAME
        or not check_password_hash(ADMIN_PASSWORD_HASH, password)
    ):
        return jsonify({
            "success": False,
            "message": "Invalid username or password."
        }), 401

    session.clear()
    session["admin_logged_in"] = True

    return jsonify({
        "success": True,
        "message": "Admin login successful."
    })


# Admin logout API
@app.route("/api/logout", methods=["POST"])
def admin_logout():

    session.clear()

    return jsonify({
        "success": True,
        "message": "Logged out successfully."
    })


# Check login session API
@app.route("/api/session", methods=["GET"])
def check_session():

    return jsonify({
        "success": True,
        "logged_in": bool(session.get("admin_logged_in"))
    })


# Load FaceNet only when the first recognition request arrives
face_engine = None


def get_face_engine():
    global face_engine

    if face_engine is None:
        face_engine = FaceEngine()

    return face_engine


# Health check API (public)
@app.route("/api/health", methods=["GET"])
def health():

    return jsonify({
        "success": True,
        "message": "Student Attendance API is running."
    })


# Get registered students (login required)
@app.route("/api/students", methods=["GET"])
@login_required
def get_students():

    connection = get_connection()

    try:
        students = pd.read_sql_query("""
            SELECT
                student_id,
                full_name,
                department,
                year
            FROM students
            ORDER BY student_id
        """, connection)

        return jsonify({
            "success": True,
            "students": students.to_dict(orient="records")
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500

    finally:
        connection.close()


# Get attendance records (login required)
@app.route("/api/attendance", methods=["GET"])
@login_required
def get_attendance():

    selected_date = request.args.get(
        "date",
        date.today().strftime("%Y-%m-%d")
    )

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", selected_date):
        return jsonify({
            "success": False,
            "message": "Date must use YYYY-MM-DD format."
        }), 400

    connection = get_connection()

    try:
        records = pd.read_sql_query("""
            SELECT
                s.student_id,
                s.full_name,
                s.department,
                s.year,
                a.attendance_date,
                a.attendance_time,
                a.status
            FROM students s
            LEFT JOIN attendance a
                ON s.student_id = a.student_id
                AND a.attendance_date = ?
            ORDER BY
                CASE
                    WHEN a.status = 'Present' THEN 0
                    WHEN a.status = 'Absent' THEN 1
                    ELSE 2
                END,
                s.student_id
        """, connection, params=(selected_date,))

        records = records.astype(object).where(
            pd.notna(records), None
        )

        return jsonify({
            "success": True,
            "date": selected_date,
            "attendance": records.to_dict(orient="records")
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500

    finally:
        connection.close()


# Face recognition and attendance marking (login required)
@app.route("/api/recognize", methods=["POST"])
@login_required
def recognize_face():

    data = request.get_json(silent=True) or {}
    image_data = data.get("image")

    # Missing image is a bad request, not an unknown-person result.
    if not image_data:
        return jsonify({
            "success": False,
            "message": "No image received. Please capture your face again."
        }), 400

    try:
        # Accept either a Base64 string or a browser data URL.
        if "," in image_data:
            image_data = image_data.split(",", 1)[1]

        image_bytes = base64.b64decode(
            image_data,
            validate=True
        )

        if len(image_bytes) > 8 * 1024 * 1024:
            return jsonify({
                "success": False,
                "message": "Image is too large. Please capture a smaller image."
            }), 413

        image = Image.open(
            BytesIO(image_bytes)
        ).convert("RGB")

    except (
        binascii.Error,
        ValueError,
        UnidentifiedImageError
    ):
        return jsonify({
            "success": False,
            "message": "Invalid image. Please capture another photograph."
        }), 400

    except Exception:
        return jsonify({
            "success": False,
            "message": "Could not process the captured image."
        }), 400

    try:
        engine = get_face_engine()
        embedding = engine.extract_embedding(image)

        if embedding is None:
            return jsonify({
                "success": False,
                "message": "No clear single face detected. Please try again."
            }), 400

        match = find_best_match(embedding)

        # Unknown face is a normal recognition result.
        # HTTP 200 prevents the frontend from treating it as
        # an expired administrator session (401).
        if match is None:
            return jsonify({
                "success": False,
                "message": "Unknown person detected. Attendance was not marked."
            }), 200

        marked, message = mark_attendance(match["student_id"])

        return jsonify({
            "success": marked,
            "message": message,
            "student": {
                "student_id": match["student_id"],
                "name": match["name"],
                "department": match["department"],
                "similarity": round(float(match["similarity"]), 4)
            }
        }), 200 if marked else 409

    except Exception as error:
        app.logger.exception("Face recognition failed")

        return jsonify({
            "success": False,
            "message": f"Recognition error: {error}"
        }), 500


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )