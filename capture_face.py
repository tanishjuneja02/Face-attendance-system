import cv2

video_capture = cv2.VideoCapture(0)

print("Press SPACE to capture your photo, or 'q' to quit without saving.")

while True:
    ret, frame = video_capture.read()
    if not ret:
        break

    cv2.imshow('Press SPACE to capture', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord(' '):  # spacebar
        name = input("Enter the person's name (no spaces): ")
        filename = f"known_faces/{name}.jpg"
        cv2.imwrite(filename, frame)
        print(f"Saved as {filename}")
        break
    elif key == ord('q'):
        break

video_capture.release()
cv2.destroyAllWindows()