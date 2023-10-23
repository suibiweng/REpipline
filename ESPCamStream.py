from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server

import cv2
import numpy as np

import requests
import threading

import time
import os

'''
INFO SECTION
- if you want to monitor raw parameters of ESP32CAM, open the browser and go to http://192.168.x.x/status
- command can be sent through an HTTP get composed in the following way http://192.168.x.x/control?var=VARIABLE_NAME&val=VALUE (check varname and value in status)
'''
def filter_handler(address, *args):
    if address == '/TakePhoto':
        print(args)

    print(f"{address}: {args}")



    



# ESP32 URL
URL = "http://192.168.0.130"

AWB = True

# Face recognition and opencv setup
cap = cv2.VideoCapture(URL + ":81/stream")
# face_classifier = cv2.CascadeClassifier('haarcascade_frontalface_alt.xml') # insert the full path to haarcascade file if you encounter any problem
saveImageName = "test.jpg"
saveImageSwitch = False

# sharedinfo = {
#     "saveimagename": "test.jpg",
#     "saveimageswitch": False
# }

def capture_frame_and_save(video_capture, output_filename):
    ret, frame = video_capture.read()
    if ret:
        # obj = time.gmtime()
        # path = "img/" + str(obj.tm_mon) + str(obj.tm_mday) + str(obj.tm_hour) + str(obj.tm_min)
        # print(path)
        
        cv2.imwrite(output_filename, frame)
        print(f"Frame saved as {output_filename}")
    else:
        print("Error: Could not capture frame")

def set_resolution(url: str, index: int=10, verbose: bool=False):
    try:
        if verbose:
            resolutions = "10: UXGA(1600x1200)\n9: SXGA(1280x1024)\n8: XGA(1024x768)\n7: SVGA(800x600)\n6: VGA(640x480)\n5: CIF(400x296)\n4: QVGA(320x240)\n3: HQVGA(240x176)\n0: QQVGA(160x120)"
            print("available resolutions\n{}".format(resolutions))

        if index in [10, 9, 8, 7, 6, 5, 4, 3, 0]:
            requests.get(url + "/control?var=framesize&val={}".format(index))
        else:
            print("Wrong index")
    except:
        print("SET_RESOLUTION: something went wrong")

def set_quality(url: str, value: int=1, verbose: bool=False):
    try:
        if value >= 10 and value <=63:
            requests.get(url + "/control?var=quality&val={}".format(value))
    except:
        print("SET_QUALITY: something went wrong")

def set_awb(url: str, awb: int=1):
    try:
        awb = not awb
        requests.get(url + "/control?var=awb&val={}".format(1 if awb else 0))
    except:
        print("SET_QUALITY: something went wrong")
    return awb


def main_loop():
    while True:
        if cap.isOpened():
            ret, frame = cap.read()
            
            global saveImageSwitch
            if saveImageSwitch:
                # print("saving from the main loop")
                global saveImageName
                capture_frame_and_save(cap, saveImageName)
                saveImageSwitch = False
                

            if ret:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.equalizeHist(gray)

            cv2.imshow("frame", frame)

            key = cv2.waitKey(1)
            
            
                
            if key == ord('r'):
                idx = int(input("Select resolution index: "))
                set_resolution(URL, index=idx, verbose=True)

            elif key == ord('q'):
                val = int(input("Set quality (10 - 63): "))
                set_quality(URL, value=val)

            elif key == ord('a'):
                AWB = set_awb(URL, AWB)

            elif key == ord('c'):
                output_filename = input("Enter the output filename (e.g., captured_frame.jpg): ")
                capture_frame_and_save(cap, output_filename)

            elif key == 27:
                break


    
# Function to handle OSC messages
def default_handler(address, *args):
    # print(address)
    # print(args[0] + "\n")
    # if address == '/imagePath':
    #     print(args[0])
    saveFile = open("myfile.txt", "a")

    # store the info
    # on receiving message, take a photo
    if address == "/imagePath":
        print("a new frame")
        global saveImageName
        saveImageName = args[0]
        

        saveFile.write(saveImageName + "\n");
        saveFile.write(args[1])
        
        print(saveImageName)
        global saveImageSwitch
        saveImageSwitch = True

    saveFile.close();

            

if __name__ == '__main__':
    set_resolution(URL, index=7)
    
    # dispatcher = Dispatcher()
    # dispatcher.map("/TakePhoto", filter_handler)
    # server = osc_server.ThreadingOSCUDPServer(
    #   ('127.0.0.1',8888), dispatcher)
    # print("Serving on {}".format(server.server_address))
    # print("Reality Editor pipeline server is On/Press Esc to exit")
    # server.serve_forever()
    # dispatcher = Dispatcher()
    # dispatcher.map("/PromtGenerateModel", filter_handler)

    # Create a thread for the camera
    main_thread = threading.Thread(target=main_loop)
    main_thread.start()
    


    # osc
    dispatcherosc = Dispatcher()
    dispatcherosc.map("/filter", print)
    dispatcherosc.set_default_handler(default_handler)


    # Create an OSC server thread
    osc_server = osc_server.ThreadingOSCUDPServer(('192.168.0.198', 6161), dispatcherosc)  # Change the IP and port as needed
    osc_server.serve_forever()
    
    


    # Wait for the main thread to finish (you can continue with other tasks here)
    main_thread.join()




    cv2.destroyallwindows()
    cap.release()