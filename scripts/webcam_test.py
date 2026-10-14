"""Manual check that the webcam works (not part of the automatic tests).

Run:  python scripts/webcam_test.py      Press q to quit.
"""
import cv2

camera = cv2.VideoCapture(0)
if not camera.isOpened():
    raise SystemExit("Could not open the webcam.")

print("Webcam opened. Press q to quit.")
while True:
    ok, frame = camera.read()
    if not ok:
        print("Failed to read a frame.")
        break
    cv2.imshow("Webcam test", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
