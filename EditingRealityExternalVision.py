import sys
import numpy as np
import cv2
import requests
import NDIlib as ndi
import threading
import time

# Global variables for frames
ndi_frame = None
ipcam_frame = None
zoom_factor = 1.3

# Function to receive and display the NDI stream
def ndi_receiver():
    global ndi_frame

    if not ndi.initialize():
        print("Cannot initialize NDI")
        return 0

    ndi_find = ndi.find_create_v2()

    if ndi_find is None:
        print("Cannot create NDI find")
        return 0

    sources = []
    while not len(sources) > 0:
        print('Looking for NDI sources...')
        ndi.find_wait_for_sources(ndi_find, 1000)
        sources = ndi.find_get_current_sources(ndi_find)

    print("NDI sources found:", sources)
    ndi_recv_create = ndi.RecvCreateV3()
    ndi_recv_create.color_format = ndi.RECV_COLOR_FORMAT_BGRX_BGRA

    ndi_recv = ndi.recv_create_v3(ndi_recv_create)

    if ndi_recv is None:
        print("Cannot create NDI receiver")
        return 0

    ndi.recv_connect(ndi_recv, sources[0])

    ndi.find_destroy(ndi_find)

    while True:
        t, v, _, _ = ndi.recv_capture_v2(ndi_recv, 5000)

        if t == ndi.FRAME_TYPE_VIDEO:
            frame = np.copy(v.data)
            ndi.recv_free_video_v2(ndi_recv, v)
            # Convert 4-channel BGRX_BGRA to 3-channel BGR
            ndi_frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        if cv2.waitKey(1) & 0xff == 27:
            break

    ndi.recv_destroy(ndi_recv)
    ndi.destroy()

# Function to receive and display the IP camera stream
def ipcam_receiver(url):
    global ipcam_frame

    while True:
        try:
            cap = requests.get(url, stream=True, timeout=10)
            if cap.status_code == 200:
                bytes = b''
                for chunk in cap.iter_content(chunk_size=1024):
                    bytes += chunk
                    a = bytes.find(b'\xff\xd8')
                    b = bytes.find(b'\xff\xd9')
                    if a != -1 and b != -1:
                        jpg = bytes[a:b+2]
                        bytes = bytes[b+2:]
                        ipcam_frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            else:
                print("Failed to connect to the server, status code:", cap.status_code)
                time.sleep(5)  # Wait before trying to reconnect
        except requests.exceptions.RequestException as e:
            print("Connection error:", e)
            time.sleep(5)  # Wait before trying to reconnect
        except Exception as e:
            print("An unexpected error occurred:", e)
            time.sleep(5)  # Wait before trying to reconnect

# Function to resize frames to the same height
def resize_frames_to_same_height(frame1, frame2):
    height1, width1 = frame1.shape[:2]
    height2, width2 = frame2.shape[:2]

    if height1 > height2:
        new_width2 = int(width2 * height1 / height2)
        frame2 = cv2.resize(frame2, (new_width2, height1))
    else:
        new_width1 = int(width1 * height2 / height1)
        frame1 = cv2.resize(frame1, (new_width1, height2))

    return frame1, frame2

# Function to apply zoom to the NDI frame
def apply_zoom(frame, zoom_factor):
    height, width = frame.shape[:2]
    center_x, center_y = width // 2, height // 2
    new_width, new_height = int(width * zoom_factor), int(height * zoom_factor)

    left = max(center_x - new_width // 2, 0)
    right = min(center_x + new_width // 2, width)
    top = max(center_y - new_height // 2, 0)
    bottom = min(center_y + new_height // 2, height)

    zoomed_frame = frame[top:bottom, left:right]
    zoomed_frame = cv2.resize(zoomed_frame, (width, height))
    return zoomed_frame

# Main function to display both streams side by side
def main():
    global ndi_frame, ipcam_frame, zoom_factor

    # URL of the IP camera feed
    url = "http://192.168.0.134:8001/video_feed"

    # Start the NDI receiver thread
    ndi_thread = threading.Thread(target=ndi_receiver)
    ndi_thread.daemon = True
    ndi_thread.start()

    # Start the IP camera receiver thread
    ipcam_thread = threading.Thread(target=ipcam_receiver, args=(url,))
    ipcam_thread.daemon = True
    ipcam_thread.start()

    while True:
        if ndi_frame is not None and ipcam_frame is not None:
            zoomed_ndi_frame = apply_zoom(ndi_frame, zoom_factor)
            zoomed_ndi_frame, ipcam_frame = resize_frames_to_same_height(zoomed_ndi_frame, ipcam_frame)
            combined_frame = np.hstack((zoomed_ndi_frame, ipcam_frame))
            cv2.imshow('Combined Stream', combined_frame)
        elif ndi_frame is not None:
            zoomed_ndi_frame = apply_zoom(ndi_frame, zoom_factor)
            cv2.imshow('NDI Stream', zoomed_ndi_frame)
        elif ipcam_frame is not None:
            cv2.imshow('IP Camera Stream', ipcam_frame)

        key = cv2.waitKey(1) & 0xff
        if key == 27:  # Escape key
            break
        elif key == ord('='):  # Zoom in
            zoom_factor += 0.1
        elif key == ord('-'):  # Zoom out
            zoom_factor = max(zoom_factor - 0.1, 0.1)  # Prevent zooming out too much

    cv2.destroyAllWindows()

if __name__ == "__main__":
    sys.exit(main())
