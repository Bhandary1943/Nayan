import streamlit as st
import face_recognition
import cv2
import sqlite3
import requests
import numpy as np
from io import BytesIO
import os

# Initialize database
DB_PATH = "face_recognition.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS faces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    image BLOB,
    encoding BLOB
)
""")
conn.commit()

# ESP32-CAM URL (Update to your ESP32 IP)
esp32_cam_url = "http://192.168.80.81/capture"

def capture_image():
    try:
        response = requests.get(esp32_cam_url, timeout=10)
        if response.status_code == 200:
            image_data = np.frombuffer(response.content, np.uint8)
            frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
            return frame
    except requests.RequestException as e:
        st.error(f"Error fetching image: {e}")
    return None

def save_face(name, image):
    c.execute("SELECT name FROM faces WHERE name = ?", (name,))
    if c.fetchone():
        st.warning("This name already exists in the database.")
        return
    encoding = face_recognition.face_encodings(image)
    if encoding:
        encoding_blob = sqlite3.Binary(np.array(encoding[0]).tobytes())
        _, buffer = cv2.imencode(".jpg", image)
        c.execute("INSERT INTO faces (name, image, encoding) VALUES (?, ?, ?)",
                  (name, buffer.tobytes(), encoding_blob))
        conn.commit()
        st.success(f"Face added: {name}")
    else:
        st.warning("No face detected in the image.")

def load_known_faces():
    c.execute("SELECT name, encoding FROM faces")
    data = c.fetchall()
    known_encodings = []
    known_names = []
    for name, encoding_blob in data:
        encoding = np.frombuffer(encoding_blob, dtype=np.float64)
        known_encodings.append(encoding)
        known_names.append(name)
    return known_encodings, known_names

def recognize_faces(image):
    encodings = face_recognition.face_encodings(image)
    if not encodings:
        st.warning("No faces detected.")
        return []
    known_encodings, known_names = load_known_faces()
    recognized_names = []
    for encoding in encodings:
        matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=0.45)
        if True in matches:
            matched_idx = matches.index(True)
            recognized_names.append(known_names[matched_idx])
        else:
            recognized_names.append("Unknown")
    return recognized_names

def delete_face(name):
    c.execute("DELETE FROM faces WHERE name = ?", (name,))
    conn.commit()
    st.success(f"Deleted face: {name}")

def main():
    st.title("ESP32-CAM Face Recognition")

    # ---- Recognize Face ----
    if st.button("Capture Image & Recognize Face"):
        image = capture_image()
        if image is not None:
            recognized_names = recognize_faces(image)
            st.image(image, caption=f"Recognized: {', '.join(recognized_names)}", use_column_width=True)
            for name in recognized_names:
                st.info(f"Detected: {name}")

    # ---- Add Face ----
    st.header("Add New Face")
    name = st.text_input("Enter Name:")
    uploaded_file = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])
    if uploaded_file and name:
        if st.button("Upload Face"):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            save_face(name, image)

    # ---- Delete Face ----
    st.header("Delete Face")
    c.execute("SELECT name FROM faces")
    names = [row[0] for row in c.fetchall()]
    if names:
        selected_name = st.selectbox("Select Name to Delete:", names)
        if st.button("Delete Face"):
            delete_face(selected_name)
    else:
        st.info("No faces available in the database.")

    # ---- Download Updated DB ----
    with open(DB_PATH, "rb") as f:
        st.download_button("Download Updated DB", f, file_name="face_recognition.db")

if __name__ == "__main__":
    main()
