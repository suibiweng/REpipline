import cv2
import numpy as np
import requests
import time

def main():
    url = "http://10.0.0.60:8001/video_feed"

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
                        img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        cv2.imshow('IP Camera Stream', img)

                        if cv2.waitKey(1) == 27:
                            break
            else:
                print("Failed to connect to the server, status code:", cap.status_code)
                time.sleep(5)  # Wait before trying to reconnect
        except requests.exceptions.RequestException as e:
            print("Connection error:", e)
            time.sleep(5)  # Wait before trying to reconnect
        except Exception as e:
            print("An unexpected error occurred:", e)
            time.sleep(5)  # Wait before trying to reconnect

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
