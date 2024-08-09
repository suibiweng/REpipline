import sys
import numpy as np
import cv2
import requests
import NDIlib as ndi
import threading
import time
from pythonosc import dispatcher, osc_server
from pythonosc.udp_client import SimpleUDPClient

import mediapipe as mp
import time
from pathlib import Path

mp_objectron = mp.solutions.objectron
mp_drawing = mp.solutions.drawing_utils

# Global variables for frames
ndi_frame = None
ipcam_frame = None
campoints = None
isTracking=False


VRip='192.168.0.213'

objectron = mp_objectron.Objectron(static_image_mode=False,
                            max_num_objects=1,
                            min_detection_confidence=0.5,
                            min_tracking_confidence=0.3,
                            model_name='Camera')

#'Cup', 'Shoe', 'Camera' and 'Chair'.

def iniDetection(model_name):
    objectron = mp_objectron.Objectron(static_image_mode=False,
                            max_num_objects=1,
                            min_detection_confidence=0.5,
                            min_tracking_confidence=0.3,
                            model_name='Camera')
    
    
    



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
                        
                        if(isTracking):
                            results = objectron.process(ipcam_frame)
                            if results.detected_objects:
                             for detected_object in results.detected_objects:
            #print(detected_object)
                                mp_drawing.draw_landmarks(ipcam_frame, 
                                      detected_object.landmarks_2d, 
                                      mp_objectron.BOX_CONNECTIONS)
          
                                mp_drawing.draw_axis(ipcam_frame, 
                                    detected_object.rotation,
                                    detected_object.translation)
                                 # print (detected_object.rotation+" "+detected_object.translation)
                        
                        
                        
                        
                        
                        
                        
                        
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

# OSC message handler
def InpaintBackGround(address, *args):
    global campoints

    if address == "/InpaintBackGround":
        urid = args[0]
    #    // print(urid)
        campoints = (int(args[1]), int(args[2]))
        adjPointDepth = (0,0)
        adjPointRGB = (0,0)
        if ndi_frame is not None:
            # Draw a dot on the NDI frame at the specified campoints
            cv2.circle(ndi_frame,(campoints[0]-50,campoints[1]+250), 10, (0, 0, 255), -1)  # Red dot
            # cv2.imwrite(f"{urid}_Depth.png", ndi_frame)
        if ipcam_frame is not None:
            cv2.circle(ipcam_frame, (campoints[0]-50,campoints[1]+150), 10, (0, 0, 255), -1)
        
            # cv2.imwrite(f"{urid}.png", ipcam_frame)

        print(f"Saved frames with URID: {urid} and campoints: {campoints}")
        
        
def tracker_handler(address, *args):
    global campoints

    if address == "/SetTracker":
        urid = args[0]
    #    // print(urid)
        isTracking=True
        iniDetection(args[1])
        
        
        
def sendPositiontoVR(rotation,translation):
    
    data2 = [translation, rotation]
    send_osc_message(VRip, 1337, "/GenrateModel", data2)
    
    

def send_osc_message(ip, port, address, data):
    try:
        client = SimpleUDPClient(ip, port)  # Create client
        client.send_message(address, data)  # Send OSC message
    except Exception as e:
        print(f"Error sending OSC message: {e}")


def getallAddress(address, *args):
    
    if address == "/startRecord":
        print("start to")
        serials_data = []
        imgPath ="./output/"+args[0]+"/"  
        URLid=args[0]
        # Create a Path object
        imgPath_obj = Path(imgPath)
        jsonFilename="./output/"+args[0]+"/" +args[0]+".json"
        imgPath_obj.mkdir(parents=True, exist_ok=True)
    
    if address == "/imagePath":
        #saveFile = open(imgPath+"/data.txt", "w")
        print("a new frame")
        print(args[0])
        saveImageName = imgPath+args[0]
        serials_data.append({"Filename": args[0], "Coordinates":  convert_coordinates(args[1])})
        picCount+=1
        
        
        

        #saveFile.write(saveImageName + "\n")
        #saveFile.write(args[1])
        
        print(saveImageName)
        global saveImageSwitch
        saveImageSwitch = True




    
    
        
    

# Function to start the OSC server'192.168.0.139', 6161
def start_osc_server(ip="192.168.0.139", port=6161):
    disp = dispatcher.Dispatcher()
    disp.map("/InpaintBackGround", InpaintBackGround)
    disp.map("/SetTracker", tracker_handler)
    #disp.set_default_handler(default_handler)

    server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
    print(f"OSC server running on {ip}:{port}")
    server.serve_forever()

# Main function to display both streams side by side
def main():
    global ndi_frame, ipcam_frame

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

    # Start the OSC server thread
    osc_thread = threading.Thread(target=start_osc_server)
    osc_thread.daemon = True
    osc_thread.start()

    while True:
        if ndi_frame is not None and ipcam_frame is not None:
            ndi_frame, ipcam_frame = resize_frames_to_same_height(ndi_frame, ipcam_frame)
            combined_frame = np.hstack((ndi_frame, ipcam_frame))
            cv2.imshow('Combined Stream', combined_frame)
        elif ndi_frame is not None:
            cv2.imshow('NDI Stream', ndi_frame)
        elif ipcam_frame is not None:
            cv2.imshow('IP Camera Stream', ipcam_frame)

        if cv2.waitKey(1) & 0xff == 27:
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    sys.exit(main())

