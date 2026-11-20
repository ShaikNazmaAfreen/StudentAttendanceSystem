
import streamlit as st
from PIL import Image

from app.face_engine import FaceEngine
from app.recognition import find_best_match
from app.attendance import mark_attendance
from app.dashboard import show_dashboard


st.set_page_config(
    page_title="Student Attendance System",
    page_icon="🎓",
    layout="wide"
)


@st.cache_resource
def load_face_engine():
    return FaceEngine()


# Sidebar navigation
st.sidebar.title("🎓 Student Attendance")
page = st.sidebar.radio(
    "Navigation",
    ["Mark Attendance", "Admin Dashboard"]
)


# PAGE 1: MARK ATTENDANCE
if page == "Mark Attendance":

    st.title("🎓 Smart Student Attendance System")
    st.write("Face Recognition-Based Attendance Management")

    st.divider()

    st.subheader("Mark Your Attendance")

    st.info(
        "Position your face clearly in front of the camera. "
        "Only registered students can mark attendance."
    )

    try:
        with st.spinner("Loading FaceNet model..."):
            face_engine = load_face_engine()

        st.success("Face recognition system is ready!")

    except Exception as error:
        st.error(f"Could not load FaceNet: {error}")
        st.stop()

    captured_image = st.camera_input("Capture your face")

    if captured_image is not None:

        image = Image.open(captured_image).convert("RGB")

        st.image(
            image,
            caption="Captured photograph",
            width=300
        )

        if st.button("Recognize Face and Mark Attendance"):

            with st.spinner("Recognizing your face..."):

                try:
                    embedding = face_engine.extract_embedding(image)

                    if embedding is None:

                        st.error(
                            "No clear single face detected. "
                            "Please capture another photograph."
                        )

                    else:

                        match = find_best_match(embedding)

                        if match is None:

                            st.error("Unknown person detected!")
                            st.warning(
                                "Your identity could not be verified. "
                                "Attendance was NOT marked."
                            )

                        else:

                            success, message = mark_attendance(
                                match["student_id"]
                            )

                            st.subheader("Recognition Result")

                            st.write("Student ID:", match["student_id"])
                            st.write("Name:", match["name"])
                            st.write("Department:", match["department"])
                            st.write(
                                "Similarity:",
                                f'{match["similarity"]:.4f}'
                            )

                            if success:
                                st.success(message)
                            else:
                                st.warning(message)

                except Exception as error:
                    st.error(f"An error occurred: {error}")


# PAGE 2: ADMIN DASHBOARD
elif page == "Admin Dashboard":

    show_dashboard()


st.divider()

st.caption(
    "Smart Face Recognition-Based Student Attendance Management System"
)
