from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
import subprocess

import cv2
import numpy as np

import requests
import threading

import time
import os

from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import NDIlib as ndi



class filecrateHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        # Check if the created file is "transform.json"
        if event.src_path.endswith("transform.json"):
            print(f"File 'transform.json' has been created at {event.src_path}")


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

# face_classifier = cv2.CascadeClassifier('haarcascade_frontalface_alt.xml') # insert the full path to haarcascade file if you encounter any problem
saveImageName = "test.jpg"
saveImageSwitch = False
imgPath = ""

# sharedinfo = {
#     "saveimagename": "test.jpg",
#     "saveimageswitch": False
# }

        
def capture_frame_and_save(video_capture, output_filename):

        # obj = time.gmtime()
        # path = "img/" + str(obj.tm_mon) + str(obj.tm_mday) + str(obj.tm_hour) + str(obj.tm_min)
        # print(path)
        global imgPath
        myImgPath = imgPath + "/" +output_filename
        print(myImgPath)
        cv2.imwrite(myImgPath, video_capture)
        print(f"Frame saved")
  

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



URL = "http://192.168.0.128"

AWB = True

# Face recognition and opencv setup


def main_loop():
    
    if not ndi.initialize():
        return 0

    ndi_find = ndi.find_create_v2()

    if ndi_find is None:
        return 0

    sources = []
    while not len(sources) > 0:
        print('Looking for sources ...')
        ndi.find_wait_for_sources(ndi_find, 1000)
        sources = ndi.find_get_current_sources(ndi_find)

    ndi_recv_create = ndi.RecvCreateV3()
    ndi_recv_create.color_format = ndi.RECV_COLOR_FORMAT_BGRX_BGRA

    ndi_recv = ndi.recv_create_v3(ndi_recv_create)

    if ndi_recv is None:
        return 0

    ndi.recv_connect(ndi_recv, sources[0])
    ndi.find_destroy(ndi_find)
    
    
    
    
    while True:
        
        t, v, _, _ = ndi.recv_capture_v2(ndi_recv, 5000)

        if t == ndi.FRAME_TYPE_VIDEO:
            #print('Video data received (%dx%d).' % (v.xres, v.yres))
            frame = np.copy(v.data)
            cv2.imshow('ndi image', frame)
            ndi.recv_free_video_v2(ndi_recv, v)
        
        
        
            
            
            global saveImageSwitch
            if saveImageSwitch:
                # print("saving from the main loop")
                global saveImageName
                capture_frame_and_save(frame, saveImageName)
                saveImageSwitch = False
                

            

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
                capture_frame_and_save(frame, output_filename)

            elif key == 27:
                break
            
class MyHandler(FileSystemEventHandler):
    def __init__(self, subprocess_to_terminate):
        self.subprocess = subprocess_to_terminate

    def on_created(self, event):
        if event.is_directory:
            print(f"Directory created: {event.src_path}")
            print("Terminating trainCommand subprocess...")
            self.subprocess.send_signal(subprocess.CTRL_C_EVENT)

class SubdirHandler(FileSystemEventHandler):
    def __init__(self, target_file):
        self.target_file = target_file

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(self.target_file):
            print(f"File created: {event.src_path}")

def processData(path):
    
    ProcessCommand = f"python .\scripts\colmap2nerf.py --run_colmap --images {path} --out {path}\transforms.json"
        # Run the trainCommand subprocess and capture its output0101
    train_process = subprocess.Popen(ProcessCommand, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    train_process_stdout, _ = train_process.communicate()
    print("")


def instNGP(nerfTransform):
    ProcessCommand = f"python ./scripts/run.py --training_data .\data\nerf\Bunny\transforms.json --save_snapshot .\data\Bunny-50-35000.ingp --n_steps 2000 --save_mesh .\data\Bunny.obj"
        # Run the trainCommand subprocess and capture its output0101
    train_process = subprocess.Popen(ProcessCommand, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    train_process_stdout, _ = train_process.communicate()


def activate_anaconda_environment(environment_name):
    try:
        # Construct the command to activate the Anaconda environment
        command = f"conda activate {environment_name}"

        # Use subprocess to run the command in the shell
        subprocess.run(command, shell=True, check=True)

        print(f"Activated Anaconda environment: {environment_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error activating Anaconda environment: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


# Function to handle OSC messages
def default_handler(address, *args):
    if address == "/start":
        print("start")
        obj = time.gmtime()
        global imgPath
        imgPath ="/output/"+ str(obj.tm_mon) + str(obj.tm_mday) + str(obj.tm_hour) + str(obj.tm_min)
        folder_path = Path(imgPath)
        
        
        print(folder_path)
        folder_path.mkdir(parents=True, exist_ok=True)
        # if not folder_path.exists():
        #     folder_path.mkdir()
        #     print(f"Folder '{imgPath}' created successfully.")
        # else:
        #     print(f"Folder '{imgPath}' already exists.")

    # store the info
    # on receiving message, take a photo
    if address == "/imagePath":
        #saveFile = open(imgPath+"/data.txt", "w")
        print("a new frame")
        global saveImageName
        saveImageName = args[0]
        

        #saveFile.write(saveImageName + "\n")
        #saveFile.write(args[1])
        
        print(saveImageName)
        global saveImageSwitch
        saveImageSwitch = True
        #saveFile.close()
    
    if address == "/end":
        print("finish recording")
        # for debugging
        # imgPath = "output/10191312"        

        # outputImgPath = imgPath+"Out"
        # # Define the command you want to run within the Conda environment
        # command = f"ns-process-data images --data {imgPath} --output-dir {outputImgPath}"
        # subprocess.run(command, shell=True)
        # print("preprocess data done")
        
        # trainCommand = f"ns-train nerfacto --data {outputImgPath}"
        # # Run the trainCommand subprocess and capture its output
        # train_process = subprocess.Popen(trainCommand, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # train_process_stdout, _ = train_process.communicate()

        # # Parse the output to find the most recently created directory
        # output_lines = train_process_stdout.decode("utf-8").splitlines()
        # most_recent_directory = None
        # for line in output_lines:
        #     if line.startswith("    timestamp"):
        #         print(line)
        #         most_recent_directory = line[len("    timestamp")+2:]
        #         most_recent_directory = most_recent_directory[:-2]
        #         print(most_recent_directory)
        #         break

        # if most_recent_directory:
        #     most_recent_directory = "outputs/" + outputImgPath[7:] + "/nerfacto/" + most_recent_directory
        #     print(most_recent_directory)
        #     most_recent_directory = os.path.abspath(most_recent_directory)

        #     # Start monitoring the most recently created directory
        #     event_handler = MyHandler(train_process)
        #     observer = Observer()
        #     observer.schedule(event_handler, path=most_recent_directory, recursive=False)
        #     observer.start()

        #     # Start monitoring for the "text.txt" file in the subdirectory
        #     subdirectory = os.path.join(most_recent_directory, "subdirectory_name")  # Replace "subdirectory_name" with the actual subdirectory name
        #     sub_event_handler = SubdirHandler("dataparser_transforms.json")
        #     sub_observer = Observer()
        #     sub_observer.schedule(sub_event_handler, path=subdirectory, recursive=False)
        #     sub_observer.start()

        #     try:
        #         while train_process.poll() is None:
        #             time.sleep(1)
        #     except KeyboardInterrupt:
        #         observer.stop()
        #         observer.join()
        #         sub_observer.stop()
        #         sub_observer.join()
        # else:
        #     print("No directory found to monitor.")
        
def oscinit():
    global osc_server
    dispatcherosc = Dispatcher()
   # osc_server = osc_server.ThreadingOSCUDPServer(('127.0.0.1', 6161), dispatcherosc)  # Change the IP and port as needed
    osc_server=osc_server.ThreadingOSCUDPServer(('127.0.0.1', 6161), dispatcherosc)
    OSCserver_thread = threading.Thread(target=osc_server.serve_forever)
    OSCserver_thread.start()
    
    
    
    #  OSCserver = osc_server.ForkingOSCUDPServer((OSCaddress, OSCport), dispatcher)
    # OSCserver_thread = threading.Thread(target=OSCserver.serve_forever)
    # OSCserver_thread.start()
    print("Serving on {}".format(osc_server.server_address))
    print("Reality Editor pipeline server is On/Press Esc to exit")
   # osc_server.serve_forever()

    dispatcherosc.map("/filter", print)
    dispatcherosc.set_default_handler(default_handler)
    

            

if __name__ == '__main__':
    #set_resolution(URL, index=7)
    # dispatcher = Dispatcher()
    # dispatcher.map("/TakePhoto", filter_handler)
    # server = osc_server.ThreadingOSCUDPServer(
    #   ('127.0.0.1',8888), dispatcher)
    # print("Serving on {}".format(server.server_address))
    # print("Reality Editor pipeline server is On/Press Esc to exit")
    # server.serve_forever()
    # dispatcher = Dispatcher()
    # dispatcher.map("/PromtGenerateModel", filter_handler)
    
    
    main_thread = threading.Thread(target=main_loop)
    main_thread.start()
    oscinit()
    
    
    
    
    #dispatcherosc = Dispatcher()



    # Create an OSC server thread
    # osc_server = osc_server.ThreadingOSCUDPServer(('127.0.0.1', 6161), dispatcherosc)  # Change the IP and port as needed
    
    # print("Serving on {}".format(osc_server.server_address))
    # print("Reality Editor pipeline server is On/Press Esc to exit")
    # osc_server.serve_forever()
    
    # dispatcherosc.map("/filter", print)
    # dispatcherosc.set_default_handler(default_handler)

    # Create a thread for the camera

    


    # osc

    
    


    # Wait for the main thread to finish (you can continue with other tasks here)




    cv2.destroyallwindows()
    #cap.release()