import cv2

video_capture = cv2.VideoCapture(0)

if not video_capture.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Webcam opened successfully! Press 'q' to quit.")

while True:
    ret, frame = video_capture.read()

    if not ret:
        print("Error: Failed to grab frame.")
        break

    cv2.imshow('Webcam Test', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video_capture.release()
cv2.destroyAllWindows()