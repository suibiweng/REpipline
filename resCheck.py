import cv2

def set_camera_resolution_and_show(camera_index=1, width=2560, height=960):
    # Open a connection to the camera
    cap = cv2.VideoCapture(camera_index)

    # Check if the camera opened successfully
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    # Set the desired resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    # Verify if the resolution is set correctly
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if actual_width != width or actual_height != height:
        print(f"Warning: The camera resolution is set to {actual_width}x{actual_height} instead of {width}x{height}")

    # Capture frames and display them in a window
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture image")
            break

        # Display the frame
        cv2.imshow("Camera Feed", frame)

        # Exit the loop when 'q' key is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the camera and close the window
    cap.release()
    cv2.destroyAllWindows()

# Set the desired resolution and show the camera feed
set_camera_resolution_and_show(camera_index=1, width=2560, height=960)
