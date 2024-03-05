from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
import subprocess
import zipfile

import paramiko
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

import pymeshlab


from PIL import Image
import json



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



    





saveImageName = "test.jpg"
saveImageSwitch = False
imgPath = ""
jsonFilename=""
serials_data = []
URLid=""
picCount =0



def capture_frame_and_save(frame, output_filename):
    global imgPath
    myImgPath =  output_filename
    print(myImgPath)
    
    # Convert frame to RGB format
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Convert frame to PIL Image
    pil_image = Image.fromarray(frame_rgb)
    
    # Save the PIL Image as JPEG
    pil_image.save(myImgPath)
    
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

def ProcessBackandFront(path):
    
    ProcessCommand= f"python MaskAndBk.py --input_img {path} --point_labels 1 --dilate_kernel_size 15 --output_dir {path} --sam_model_type \"vit_h\" --sam_ckpt ./pretrained_models/sam_vit_h_4b8939.pth --lama_config ./lama/configs/prediction/default.yaml --lama_ckpt ./pretrained_models/big-lama"
    
  #  ProcessCommand = f"python .\scripts\colmap2nerf.py --run_colmap --images {path} --out {path}\transforms.json"
        # Run the trainCommand subprocess and capture its output0101
    train_process = subprocess.Popen(ProcessCommand, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    train_process_stdout, _ = train_process.communicate()
    print("")



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
        
        
def store_serials_data(serials_data, filename):
    """
    Store serials data into a JSON array and export to a .json file.

    Args:
    serials_data (list): List of dictionaries containing serials data.
    filename (str): Name of the .json file to export.
    """
    with open(filename, 'w') as json_file:
        json.dump(serials_data, json_file, indent=4)

def convert_coordinates(coordinates_str):
    """
    Convert string representation of coordinates to tuple format.

    Args:
    coordinates_str (str): String representation of coordinates like "(300,200)".

    Returns:
    tuple: Tuple format of coordinates like (300, 200).
    """
    # Remove the parentheses and split by comma
    coordinates_str = coordinates_str.strip('()')
    x, y = coordinates_str.split(',')
    # Convert to integers and return as a tuple
    return float(x), float(y)


# Function to handle OSC messages
def default_handler(address, *args):
    global imgPath
    global saveImageName
    global jsonFilename
    global serials_data
    global URLid
    global picCount
  
    if address == "/startRecord":
        
        print("start to")
        serials_data = []
        imgPath ="./output/"+args[0]+"/"  
        
        URLid=args[0]
        # Create a Path object
        imgPath_obj = Path(imgPath)
        jsonFilename="./output/"+args[0]+"/" +args[0]+".json"

        # Create the directory
        imgPath_obj.mkdir(parents=True, exist_ok=True)
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
        print(args[0])

        saveImageName = imgPath+args[0]
       
        
        serials_data.append({"Filename": args[0], "Coordinates":  convert_coordinates(args[1])})
        picCount+=1
        
        
        

        #saveFile.write(saveImageName + "\n")
        #saveFile.write(args[1])
        
        print(saveImageName)
        global saveImageSwitch
        saveImageSwitch = True
        #saveFile.close()
    
    if address == "/endRecord":
        print("finish recording")
       # store_serials_data(serials_data, jsonFilename)
      # testdata
      
        URLid="20240229125610"
        picCount=32
        serials_data.append({"Filename": "1", "Coordinates":  [282.44,231.3]})
        
        
        testpath = "./output/"+URLid
        testvideoName=URLid+".mp4"
        
        
        ffmpegCall(testpath, testvideoName, picCount)       
        
        saveImageName="" 
        jsonFilename=""
        #serials_data = []
        picCount=0
    if address =="/InstructModify":
        shape_path=find_file(f"{args[2]}_scaned.obj",".\\output")
        
        if(shape_path!=None):
            modifytheMesh(args[1],args[2],shape_path)
        
        
    
    
    if address =="/NerfTest":
        print("TestNerf")
        
        URLid="20240229125610"
        testpath = "./output/"+URLid+"\\"+URLid+"\\original_frames"
        
        testpath= os.path.abspath(testpath)
        
        BKfolderPath= "./output/"+URLid+"\\"+"GenerateImages\\Bkonly\\images\\"
        
        BKfolderPath=os.path.abspath(BKfolderPath)
        ObjPath=testpath
        
        ObjJsonPath=ColmapObj(ObjPath)
           
        if(ObjJsonPath != None):
            objdone=NerfObj (ObjJsonPath,ObjPath,"target")
     
     
     
     
        if(objdone):
            BKJsonPath=ColmapObj(BKfolderPath)
            if(BKJsonPath != None):
                Bkdone=NerfObj (BKJsonPath,BKfolderPath,"background")
        
        
        
        # if(Bkdone):
        
        
        
            
            
            
        #     zip_file_with_delay(get_obj_file(BKfolderPath),URLid+"_scaned_background.zip")
        #     time.sleep(10)
        #     zip_file_with_delay(get_obj_file(ObjPath),URLid+"_target.zip")
        
def find_file(filename, search_path, search_subdirs=True):
    """
    Searches for a file within a specified path and its subdirectories.

    Args:
    - filename (str): The name of the file to search for.
    - search_path (str): The directory path to start the search from.
    - search_subdirs (bool, optional): Whether to search in subdirectories. Defaults to True.

    Returns:
    - str or None: The path to the file if found, None otherwise.
    """
    for root, dirs, files in os.walk(search_path):
        if filename in files:
            return os.path.join(root, filename)
    return None
    
    
    
    
    
    
    
def modifytheMesh(prompt,UID,shapePth):
    #result = subprocess.run(f"python C:\\Users\\someo\\Desktop\\RealityEditor\\PythonProject\\Inpaint-Anything\\TracktheTarget.py --video_path  {output_dir}\\{str(video_path)} --coordinates {int(coordinates[0])} {int(coordinates[1])} --output_dir {output_dir}")
    result=f"python TextureChangePipeline.py --URID {UID} --prompt {prompt} --ShapePath {shapePth}"
    # Check if the command was executed successfully
    if result.returncode == 0:
        print("Command executed successfully.")
       
        
        

        
        # Optional: Print stdout
        if result.stdout:
            print("Output:", result.stdout)
        
    else:
        print("Command failed with return code", result.returncode)
        # Print stderr for error
        if result.stderr:
            print("Error:", result.stderr)
    
        

def process_obj_and_save(input_obj_path):
    """
    Processes an OBJ file using PyMeshlab with the following steps:
    1. Merge close vertices
    2. Remove isolated pieces based on a diameter threshold
    3. Apply trivial per-triangle parameterization
    4. Transfer vertex attributes to texture

    It then saves the processed OBJ, associated MTL, and generated PNG files 
    into a folder named after the input OBJ file.

    Parameters:
    - input_obj_path: str, the path to the input OBJ file

    Returns:
    - folder_path: str, the path to the folder containing the processed files
    """
    base_name = os.path.splitext(os.path.basename(input_obj_path))[0]
    output_folder = os.path.join(os.path.dirname(input_obj_path), base_name)

    os.makedirs(output_folder, exist_ok=True)

    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(input_obj_path)

    # Merge close vertices
       # create a new object of type PercentageValue, with value 50%
    p = pymeshlab.PercentageValue(1)

    # apply the filter that will remove connected components having diameter less than 50%
    # of the diameter of the entire mesh
    ms.meshing_merge_close_vertices(threshold =p)# Adjust targetdistance as needed

    # Remove isolated pieces
    # Here we adjust the filter to what is believed to be correct; you may need to replace this with the correct function and parameters
    # Check your PyMeshlab version for the exact filter name and parameters
    p = pymeshlab.PercentageValue(10)
    ms.meshing_remove_connected_component_by_diameter(mincomponentdiag=p)




    # Trivial per-triangle parameterization and vertex attribute to texture might not be directly available in all PyMeshLab versions
    # This step assumes functionality exists or is similarly named
    ms.compute_texcoord_parametrization_triangle_trivial_per_wedge(sidedim=0,textdim=1024,border=0,method='Basic')
    
    
    ms.compute_texmap_from_color(textname="1.png",textw =1024,texth=1024)
    
    
    

    processed_obj_path = os.path.join(output_folder, base_name + '.obj')
    ms.save_current_mesh(processed_obj_path)

    return output_folder


def ffmpegCall(input_folder, output_video, frame_rate=30):
    """
    Convert a folder of pictures into a video using ffmpeg.

    Parameters:
    - input_folder: Path to the folder containing the pictures.
    - output_video: Path and filename of the output video file.
    - frame_rate: Frame rate of the output video in frames per second.

    The pictures must be named in a sequence (e.g., img001.jpg, img002.jpg, etc.).
    """
    global URLid

    # Construct the ffmpeg command
    # ffmpeg_cmd = [
    #     "ffmpeg",
    #     "-r",30,
    #     "-framerate", str(frame_rate),  # Frame rate
    #     "-pattern_type", "glob",  # Use glob pattern matching
    #     "-i", input_folder+"*.jpg",  # Input files
    #     "-c:v", "libx264",  # Video codec to use
    #     "-pix_fmt", "yuv420p",  # Pixel format, yuv420p is widely compatible
    #     output_video  # Output video file
    # ]

    # Run the ffmpeg command
    try:
        subprocess.run(f"ffmpeg -framerate 31 -i {input_folder}/{URLid}_scan_%d.jpg -c:v libx264 -pix_fmt yuv420p -r {frame_rate} {input_folder}/{output_video}", check=True)
        print(f"Video has been successfully created at {output_video}")
        time.sleep(2)
        run_tracking(output_video,serials_data[0]["Coordinates"],input_folder)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")


def run_tracking(video_path, coordinates, output_dir):
    global URLid
    #print(output_dir)
    """
    Executes the object tracking script with the given parameters.

    Parameters:
    - video_path (str): Path to the video file.
    - coordinates (list or tuple): The x and y coordinates of the object as a list or tuple.
    - output_dir (str): The directory to save the output results.

    Returns:
    - None: Prints the command's stdout and stderr.
    """
    # Ensure coordinates are passed as separate arguments
    #coordinates = list(map(str, coordinates))  # Convert each coordinate to string
    
    current_folder_path = os.getcwd()

    # Construct the command with arguments
    # command = [
        
    #     f"python C:\\Userssomeo\\Desktop\\RealityEditor\\PythonProject\\Inpaint-Anything\\TracktheTarget.py",
    #     "--video_path",current_folder_path+ str(video_path),
    #     "--coordinates", *coordinates,  # Unpack coordinates into separate arguments
    #     "--output_dir",current_folder_path+ str(output_dir)
    # ]
    


    # Execute the command
    result = subprocess.run(f"python C:\\Users\\someo\\Desktop\\RealityEditor\\PythonProject\\Inpaint-Anything\\TracktheTarget.py --video_path  {output_dir}\\{str(video_path)} --coordinates {int(coordinates[0])} {int(coordinates[1])} --output_dir {output_dir}")

    # Check if the command was executed successfully
    if result.returncode == 0:
        print("Command executed successfully.")
        time.sleep(2)
        forinpainting = os.path.abspath(output_dir+"\\"+URLid+"\\original_frames")
        print (forinpainting)
        
        run_inpainting(forinpainting,output_dir)
        
        

        
        # Optional: Print stdout
        if result.stdout:
            print("Output:", result.stdout)
        
    else:
        print("Command failed with return code", result.returncode)
        # Print stderr for error
        if result.stderr:
            print("Error:", result.stderr)
    
    
def run_inpainting(input_folder, output_dir):
    global URLid
    #print(output_dir)
    jsonFilepath=input_folder+"\\"+URLid+".json"

  
    # Execute the command
    result = subprocess.run(f"python C:\\Users\\someo\\Desktop\\RealityEditor\\PythonProject\\Inpaint-Anything\\MaskAndBk.py --input_img {input_folder} --coordsJson {jsonFilepath} --point_labels 1 --dilate_kernel_size 15 --output_dir {output_dir} --sam_model_type \"vit_h\" --sam_ckpt C:\\Users\\someo\\Desktop\\RealityEditor\\PythonProject\\Inpaint-Anything\\pretrained_models\\sam_vit_h_4b8939.pth --lama_config C:\\Users\\someo\\Desktop\\RealityEditor\\PythonProject\\Inpaint-Anything\\lama\\configs\\prediction\\default.yaml --lama_ckpt  C:\\Users\\someo\\Desktop\\RealityEditor\\PythonProject\\Inpaint-Anything\\pretrained_models/big-lama ")

    # Check if the command was executed successfully
    if result.returncode == 0:
        print("Command executed successfully.")
        time.sleep(2)
        BKfolderPath=input_folder+"\\"+"GenerateImages\\images\\"
        ObjPath=input_folder
        
        ObjJsonPath=ColmapObj(ObjPath)
           
        if(ObjJsonPath != None):
            objdone=NerfObj (ObjJsonPath,ObjPath,"target")
        else:
            print("Error in colmap")
            return False
        if(objdone):
            BKJsonPath=ColmapObj(BKfolderPath)
            if(BKJsonPath != None):
                Bkdone=NerfObj (BKJsonPath,BKfolderPath,"background")
        
        
        
        # if(Bkdone):
        #     # get_obj_file(BKfolderPath,URLid+"_scaned_background.zip")
        #     # time.sleep(10)
        #     # get_obj_file(ObjPath,URLid+"_target.zip")

        

            
        

        
        # Optional: Print stdout
        if result.stdout:
            print("Output:", result.stdout)
        
    else:
        print("Command failed with return code", result.returncode)
        # Print stderr for error
        if result.stderr:
            print("Error:", result.stderr)
    
def ColmapObj (input_folder):
    global URLid
    #print(output_dir)
    jsonFilepath=input_folder+"\\transform.json"
    cmd= f"python C:\\Users\\someo\\Desktop\\RealityEditor\\PythonProject\\instant-ngp\\scripts\\colmap2nerf.py --colmap_matcher exhaustive --run_colmap --aabb_scale 16 --images {input_folder} --out {jsonFilepath} --overwrite"

    # Execute the command
    result = subprocess.run(cmd)

    # Check if the command was executed successfully
    if result.returncode == 0:
        print("Colmap executed successfully.")
        return jsonFilepath
        # Optional: Print stdout
      
        
    else:
        print("Command failed with return code", result.returncode)
        return None
        # Print stderr for error
       
def NerfObj (input_json,output_folder,Objtype):
    global URLid
    
    cmd= f"python C:\\Users\\someo\\Desktop\\RealityEditor\\PythonProject\\instant-ngp\\scripts\\run.py --training_data {input_json} --save_snapshot {output_folder}\\{URLid}_scaned_{Objtype}.ingp --n_steps 2000 --marching_cubes_density_thresh 2.5 --marching_cubes_res 256 --save_mesh {output_folder}\\{URLid}_scaned_{Objtype}.obj" 

   # cmd= f"python C:\\Users\\someo\\Desktop\\RealityEditor\\PythonProject\\instant-ngp\\scripts\\colmap2nerf.py --colmap_matcher exhaustive --run_colmap --aabb_scale 16 --images {input_folder}--out {jsonFilepath}"

    # Execute the command
    result = subprocess.run(cmd)

    # Check if the command was executed successfully
    if result.returncode == 0:
        zip_folder_with_delay(process_obj_and_save(f"{output_folder}\\{URLid}_scaned_{Objtype}.obj"),f"{URLid}_scaned_{Objtype}.zip")
        print("Command executed successfully.")
        
        # Optional: Print stdout
        return True
        
    else:
        print("Command failed with return code", result.returncode)
        # Print stderr for error
        return False
    
    
    

def zip_file_with_delay(file_path, output_zip, delay=3):
    time.sleep(delay)

    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Determine the arcname (the name of the file within the zip archive)
        # This will be the file's base name (its name without any directory components)
        arcname = os.path.basename(file_path)
        
        # Write the file to the zip archive
        zipf.write(file_path, arcname)
        

        print("Done!")
    
    # Assuming you have a function to upload the file to a server
    return upload_file_to_server(output_zip)

def zip_folder_with_delay(folder_path, output_zip, delay=3):


    # Wait for the specified delay
    time.sleep(delay)

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Determine the arcname by removing the folder path from the file path
                arcname = os.path.relpath(file_path, folder_path)
                # Write the file to the zip archive
                zipf.write(file_path, arcname)


    print("Done!")

    # Assuming you have a function to upload the file to a server
    return upload_file_to_server(output_zip)
        



def upload_file_to_server( local_file_path,server_ip = '34.106.250.143', server_port=22):
   
    
    try:
        # 創建SSH客戶端對象
        ssh = paramiko.SSHClient()

        # 自動添加主機密鑰
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # 使用SSH金鑰進行連接
        ssh.connect(server_ip, port=server_port, username='suibidata2023', key_filename='suibikey.ppk')

        # 創建SFTP客戶端對象
        sftp = ssh.open_sftp()

        # 指定本地文件和遠程文件的路徑
        fileName = local_file_path
        remote_file_path = '/var/www/html/upload/'
        upload_file = remote_file_path + os.path.basename(fileName)

        # 上傳文件
        sftp.put(fileName, upload_file)

        # 關閉SFTP連接
        sftp.close()

        uploaded_url = f'http://{server_ip}/upload/{os.path.basename(fileName)}'  # Construct the uploaded URL
        print(f' {local_file_path} is uploaded {server_ip} at {remote_file_path}。')
        print(f'Download: {uploaded_url}')
        #send_osc_message(VRip, 1337, "/GenrateModel",[modelId,uploaded_url])
        
        return uploaded_url  # Return the uploaded URL as a string
    except Exception as e:
        print(f'Erro：{str(e)}')
        return None  # Return None in case of an error
    finally:
        # 關閉SSH連接
        ssh.close()
        


def get_obj_file(directory):
    """
    Returns the absolute path to the first file ending with '.obj' in the specified directory.

    Parameters:
    - directory (str): The path to the directory to search for an .obj file.

    Returns:
    - str: The absolute path to the first .obj file found, or None if no such file is found.
    """
    # Check if the directory exists
    if os.path.exists(directory) and os.path.isdir(directory):
        # List all files and directories in the specified directory
        for filename in os.listdir(directory):
            # Construct the full path of the file
            filepath = os.path.abspath(os.path.join(directory, filename))
            # Check if it's a file and ends with '.obj'
            if os.path.isfile(filepath) and filename.endswith('.obj'):
                return filepath  # Return the absolute path of the first .obj file found
    else:
        print(f"The directory {directory} does not exist or is not a directory.")

    return None  # Return None if no .obj file is found




        
def oscinit():
    global osc_server
    dispatcherosc = Dispatcher()
    osc_server = osc_server.ThreadingOSCUDPServer(('127.0.0.1', 6161), dispatcherosc)  # Change the IP and port as needed
    #osc_server=osc_server.ThreadingOSCUDPServer(('192.168.137.1', 6161), dispatcherosc)
    OSCserver_thread = threading.Thread(target=osc_server.serve_forever)
    OSCserver_thread.start()
    
    
    
    #  OSCserver = osc_server.ForkingOSCUDPServer((OSCaddress, OSCport), dispatcher)
    # OSCserver_thread = threading.Thread(target=OSCserver.serve_forever)
    # OSCserver_thread.start()
    print("Serving on {}".format(osc_server.server_address))
   # osc_server.serve_forever()

    dispatcherosc.map("/filter", print)
    dispatcherosc.set_default_handler(default_handler)
    

            

if __name__ == '__main__':
 
    
    
    # main_thread = threading.Thread(target=main_loop)
    # main_thread.start()
    
    try:
         oscinit()      
                
    except KeyboardInterrupt:
        exit()
       

    # Wait for the observer thread to finish
  
   
    
    
