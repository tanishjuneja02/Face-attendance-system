import cv2
import time
from deepface import DeepFace

video_capture = cv2.VideoCapture(0)
time.sleep(2)  # let the camera adjust exposure/focus

ret, frame = video_capture.read()
video_capture.release()

if ret:
    cv2.imwrite("test_photo.jpg", frame)
    print("Photo saved as test_photo.jpg")

    try:
        faces = DeepFace.extract_faces(img_path="test_photo.jpg", detector_backend="mtcnn", enforce_detection=True)
        print(f"SUCCESS: Found {len(faces)} face(s)")
    except Exception as e:
        print(f"DETECTION FAILED: {e}")
else:
    print("Could not capture from webcam")