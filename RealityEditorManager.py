from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
import subprocess
import zipfile
import yaml
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
import signal
import keyboard
import pymeshlab
from PIL import Image
import json
import sys

Inpainting_Anything_ModulePath ="C:\\Users\\someo\\Desktop\\RealityEditor\\PythonProject\\Inpaint-Anything\\"
InstantNGP_MoudlePath = "C:\\Users\\someo\\Desktop\\RealityEditor\\PythonProject\\instant-ngp\\"
TexTurePaper_modulePath=""
    

saveImageName = "test.jpg"
saveImageSwitch = False
imgPath = ""
jsonFilename=""
serials_data = []
URLid=""
picCount =0
imgPath_obj=""

ndi_frame = None
ipcam_frame = None
campoints = None
isTracking=False



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
  




URL = "http://192.168.0.128"

AWB = True
            

            
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
                        
            #             if(isTracking):
            #                 results = objectron.process(ipcam_frame)
            #                 if results.detected_objects:
            #                  for detected_object in results.detected_objects:
            # #print(detected_object)
            #                     mp_drawing.draw_landmarks(ipcam_frame, 
            #                           detected_object.landmarks_2d, 
            #                           mp_objectron.BOX_CONNECTIONS)
          
            #                     mp_drawing.draw_axis(ipcam_frame, 
            #                         detected_object.rotation,
            #                         detected_object.translation)
            else:
                print("Failed to connect to the server, status code:", cap.status_code)
                time.sleep(5)  # Wait before trying to reconnect
        except requests.exceptions.RequestException as e:
            print("Connection error:", e)
            time.sleep(5)  # Wait before trying to reconnect
        except Exception as e:
            print("An unexpected error occurred:", e)
            time.sleep(5)  # Wait before trying to reconnect

            



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
    return float(x), (float(y))



def parse_tuple_string(s):
    return tuple(map(float, s.strip('()').split(',')))
# List to hold all the received crop box data
crop_boxes = []

# Define the callback function to handle the incoming OSC message
def handle_create_crop_box(address, *args):

    # print(f"Urild:{args[0]} position:{args[1]} rotation:{args[2]} scale: {args[3]}")
    # print(f"Urild:{args[0]} position:{args[1]}")

    data = {
        "urlid": args[0],
        "position": parse_tuple_string(args[1]),
        "rotation": parse_tuple_string(args[2]),
        "scale": parse_tuple_string(args[3])
    }
    
    # Add the received data to the crop_boxes list
    crop_boxes.append(data)
    
    # Save the accumulated data to a JSON file
    with open('crop_boxes_data.json', 'w') as json_file:
        json.dump(crop_boxes, json_file, indent=4)
    
    print(f"Received and saved data: {data}")

    # print(f"Received and saved data: {data}")

# Function to handle OSC messages
def default_handler(address, *args):
    global imgPath
    global saveImageName
    global jsonFilename
    global serials_data
    global URLid
    global picCount
    global imgPath_obj
    
    #Test Message Repeat sending
    print("receive:"+address)
    print(args)
    
    
    if address== "/captureSpatialPicture":
        urid = args[0]
        campoints = (int(args[1]), int(args[2]))
        adjPointDepth = (0,0)
        adjPointRGB = (0,0)
        if ndi_frame is not None:
            # Draw a dot on the NDI frame at the specified campoints
            # cv2.circle(ndi_frame,(campoints[0]-50,campoints[1]+250), 10, (0, 0, 255), -1)  # Red dot
            cv2.imwrite(f"{urid}_Depth.png", ndi_frame)
        if ipcam_frame is not None:
            # cv2.circle(ipcam_frame, (campoints[0]-50,campoints[1]+150), 10, (0, 0, 255), -1)
            cv2.imwrite(f"{urid}_RGB.png", ipcam_frame)
        
    
    
  
    if address == "/startRecord":
        
        print("start to")
        serials_data = []
        imgPath ="./output/"+args[0]+"/"  
        URLid=args[0]
        # Create a Path object
        imgPath_obj = Path(imgPath)
        jsonFilename="./output/"+args[0]+"/" +args[0]+".json"
        imgPath_obj.mkdir(parents=True, exist_ok=True)


    # store the info
    # on receiving message, take a photo
    if address == "/imagePath":
        #saveFile = open(imgPath+"/data.txt", "w")
        print("a new frame")
        print(args[0])
        saveImageName = imgPath+args[0]
        serials_data.append({"Filename": args[0], "Coordinates":  convert_coordinates(args[1])})
        picCount+=1
        print(saveImageName)
        global saveImageSwitch
        saveImageSwitch = True
    
    if address == "/RoomScanStart":
        
        print("start to")
        serials_data = []
        imgPath ="./output/"+args[0]+"/"  
        URLid=args[0]
        # Create a Path object
        imgPath_obj = Path(imgPath)
        jsonFilename="./output/"+args[0]+"/" +args[0]+".json"
        imgPath_obj.mkdir(parents=True, exist_ok=True)
        
        
    if address == "/Roomscan":
        print("a new frame")
        print(args[0])
        saveImageName = imgPath+args[0]
        #serials_data.append({"Filename": args[0], "Coordinates":  convert_coordinates(args[1])})
        picCount+=1
        print(saveImageName)
        # global saveImageSwitch
        # saveImageSwitch = True
        #cv2.imwrite(f"{saveImageName}_Depth.png", ndi_frame)
        filename = f"{args[0]}.png"
        full_path = os.path.join(imgPath, filename) 
        cv2.imwrite(str(full_path), ipcam_frame)
        #cv2.imwrite(f"{saveImageName}_RGB.png", ipcam_frame)
   
   
   
   
    if address == "/RoomscanEnd":
        #         print("finish recording")
        # store_serials_data(serials_data, jsonFilename)
        # testdata
        # URLid="20240229125610"
        # picCount=32
        # serials_data.append({"Filename": "1", "Coordinates":  [282.44,231.3]})
        testpath = "./output/"+URLid
        testvideoName=URLid+".mp4"
        ObjJsonPath=ColmapObj(testpath)
        
        time.sleep(3)
        if(ObjJsonPath != None):
            objdone=NerfObj (ObjJsonPath,testpath,"target")
        # ffmpegCall(testpath, testvideoName, 30)       
        
        saveImageName="" 
        jsonFilename=""
        picCount=0
        imgPath_obj=""

    if address == "/endRecord":
        print("finish recording")
        store_serials_data(serials_data, jsonFilename)
        # testdata
        # URLid="20240229125610"
        # picCount=32
        # serials_data.append({"Filename": "1", "Coordinates":  [282.44,231.3]})
        
        
        testpath = "./output/"+URLid
        testvideoName=URLid+".mp4"
        time.sleep(3)
        
        ffmpegCall(testpath, testvideoName, 30)       
        
        saveImageName="" 
        jsonFilename=""
        picCount=0

    if address =="/InstructModify":
        delete_file_if_exists(f"{args[2]}_Instruction.zip")
        URLid=args[2]
        shape_path=get_output_folder_with_obj_file(args[2])

        
        if(shape_path!=None):
            # modifytheMesh(args[1],args[2],shape_path)
            yamlfile= save_yaml_file(str(args[2]), args[1], True, shape_path, 3, f"./textures/{args[2]}.yaml")
            print("StartRun Texture pipline")
            RunTheTRXURE (yamlfile)
        else:
            print("id not found!")


        
        
    if address == "/PromtGenerateModel":
        URLID=args[2]
        prompt=args[1]
        GeneratedModel(URLID,prompt)


    if address =="/NerfTest":
        print("TestNerf")
        URLid="20240311012159"
       
        testpath = "./output/"+URLid+"\\"+URLid+"\\"+URLid+"\\original_frames"
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
        
def save_yaml_file(exp_name, text, append_direction, shape_path, seed, filename):
    """
    Create YAML data similar to the provided structure and save it to a file.

    Parameters:
        exp_name (str): Experiment name.
        text (str): Text for the guide.
        append_direction (str): Direction to append.
        shape_path (str): Path to shape file.
        seed (int): Random seed.
        filename (str): Name of the file to save the YAML data.

    Returns:
        str: Absolute path of the file where the YAML data is saved.
    """
    data = {
        'guide': {
            'append_direction':True,
            'shape_path': shape_path,
            'text': f"{text}"+",{} view"
        },
        'log': {
            'exp_name': exp_name
        }, 
        'optim': {
            'seed': seed
        }
    }
    with open(filename, 'w') as file:
        yaml.dump(data, file, default_flow_style=False)
    return os.path.abspath(filename)




def delete_file_if_exists(file_path):
    """
    Deletes the file at 'file_path' if it exists.

    Args:
    file_path (str): The path to the file you want to delete.
    """
    # Check if the file exists
    if os.path.exists(file_path):
        # Delete the file
        os.remove(file_path)
        print(f"File '{file_path}' has been deleted.")
    else:
        # File does not exist
        print(f"File '{file_path}' does not exist.")


def RunTheTRXURE (YamalPath):

    global TexTurePaper_modulePath
    global URLid
    # re_export_obj(f'{TexTurePaper_modulePath}\experiments\{URLid}\mesh\mesh.obj')
    # zip_files_with_delay(f"{TexTurePaper_modulePath}\experiments\{URLid}\mesh",f"{URLid}_Instruction.zip", delay=10)


    cmd= f"python -m scripts.run_texture --config_path={YamalPath}"
    result = subprocess.run(cmd, cwd=TexTurePaper_modulePath, capture_output=True, text=True)

    # Check if the command was executed successfully
    if result.returncode == 0:
        print("Command executed successfully.")
        time.sleep(2)
        re_export_obj(f'{TexTurePaper_modulePath}\experiments\{URLid}\mesh\mesh.obj')
        zip_files_with_delay(f"{TexTurePaper_modulePath}\experiments\{URLid}\mesh",f"{URLid}_Instruction.zip", delay=10)

        

        
        # Optional: Print stdout
        if result.stdout:
            print("Output:", result.stdout)




        
    else:
        print("Command failed with return code", result.returncode)
    





        #zip_files_with_delay



        # Print stderr for error
        if result.stderr:
            print("Error:", result.stderr)
    
    return True

def zip_files_with_delay(directory, output_zip, delay=3):
    time.sleep(delay)
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Iterate through all files in the directory
        for root, _, files in os.walk(directory):
            for file in files:
                # Determine the path of the file to be zipped
                file_path = os.path.join(root, file)
                
                # Determine the arcname (the name of the file within the zip archive)
                # This will be the relative path of the file with respect to the directory
                arcname = os.path.relpath(file_path, directory)
                
                # Write the file to the zip archive
                zipf.write(file_path, arcname)
        
        print("Done!")

def re_export_obj(input_obj_file):
    # Initialize MeshLab server
    ms = pymeshlab.MeshSet()
    # Load OBJ file
    ms.load_new_mesh(input_obj_file)

    # Export as OBJ (optional: adjust export settings as needed)
    ms.save_current_mesh(input_obj_file)


# def GenratedModl(URLID,prompt):
    
#     #     parser.add_argument("--URID", required=True, help="Unique Resource Identifier")
#     #     parser.add_argument("--prompt", required=True, help="Text prompt for guide")
    
#         command = f"python shapeRuntime.py --prompt \"{prompt}\" --URID {URLID}"
#         # Execute the command
#         result = subprocess.run(command, shell=True, capture_output=True, text=True)

#         # result = subprocess.Popruen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

#         # Check if the command was executed successfully
#         if result.returncode == 0:
#             print("Command executed successfully.")
#             time.sleep(3)
#             zip_file_with_delay(f"./output/{URLID}/{URLID}_generated.FBX", f"{URLID}_generated.zip", delay=3)
            

#             # Optional: Print stdout
#             if result.stdout:
#                 print("Output:", result.stdout)
#         else:
#             print("Command failed with return code", result.returncode)
            
#             # Print stderr for error
#             if result.stderr:
#                 print("Error:", result.stderr)


def GeneratedModel(URLID, prompt):
    command = f"python shapeRuntime.py --prompt \"{prompt}\" --URID {URLID}"
    
    # Run the command in the background using Popen
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Wait for the process to complete and get output
    stdout, stderr = process.communicate()

    # Check if the command was executed successfully
    if process.returncode == 0:
        print("Command executed successfully.")
        time.sleep(3)
        zip_file_with_delay(f"./output/{URLID}/{URLID}_generated.FBX", f"{URLID}_generated.zip", delay=3)
        
        # Optional: Print stdout
        if stdout:
            print("Output:", stdout)
    else:
        print("Command failed with return code", process.returncode)
        
        # Print stderr for error
        if stderr:
            print("Error:", stderr)


        


        
def get_output_folder_with_obj_file(folder_name):
    """
    Get the path to a specified folder within the 'output' folder,
    and return the absolute path of the first .obj file found in that folder.

    Parameters:
        folder_name (str): The name of the folder you want within the 'output' folder.

    Returns:
        str: The absolute path to the specified folder within the 'output' folder.
        If a .obj file is found, returns its absolute path. Otherwise, returns None.
    """
    output_folder = os.path.join(os.getcwd(), 'output', folder_name)
    
    # Check if the specified folder exists
    if not os.path.exists(output_folder):
        return None
    
    # Look for .obj files in the specified folder
    for file_name in os.listdir(output_folder):
        if file_name.endswith('.obj') and (file_name.endswith('generated.obj') or file_name.endswith('target.obj')):
            obj_file_path = os.path.join(output_folder, file_name)
            return obj_file_path
    
    # If no .obj file found, return the path to the specified folder
    return output_folder
        
    
def modifytheMesh(prompt,UID,shapePth):
    global TexTurePaper_modulePath
    #result = subprocess.run(f"python C:\\Users\\someo\\Desktop\\RealityEditor\\PythonProject\\Inpaint-Anything\\TracktheTarget.py --video_path  {output_dir}\\{str(video_path)} --coordinates {int(coordinates[0])} {int(coordinates[1])} --output_dir {output_dir}")
    cmd=f"python TextureChangePipeline.py --URID {UID} --prompt \"{prompt}\" --ShapePath {shapePth} --ModulePath {TexTurePaper_modulePath}"
  
  
  
    result = subprocess.run(cmd,shell=True, capture_output=True, text=True)
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
    global URLid
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
    p = pymeshlab.PercentageValue(90)
    ms.meshing_remove_connected_component_by_diameter(mincomponentdiag=p)
    
    
    #simplify
    ms.meshing_decimation_quadric_edge_collapse(targetfacenum = 250000)    
    
    
    #smooth
    ms.apply_coord_laplacian_smoothing(stepsmoothnum =3)




    # Trivial per-triangle parameterization and vertex attribute to texture might not be directly available in all PyMeshLab versions
    # This step assumes functionality exists or is similarly named
    ms.compute_texcoord_parametrization_triangle_trivial_per_wedge(sidedim=0,textdim=1024,border=0,method='Basic')
    
    
    ms.compute_texmap_from_color(textname="1.png",textw =1024,texth=1024)
    
    
    

    processed_obj_path = os.path.join(output_folder, base_name + '.obj')
    ms.save_current_mesh(processed_obj_path)
    
    time.sleep(3)
    zip_folder_with_delay(output_folder,f"{base_name}.zip")

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
        subprocess.run(f"ffmpeg -framerate 30 -i {input_folder}/{URLid}_scan_%d.jpg -c:v libx264 -pix_fmt yuv420p -r 30 {input_folder}/{output_video}", check=True)
        print(f"Video has been successfully created at {output_video}")
        time.sleep(2)
        run_tracking(output_video,serials_data[0]["Coordinates"],input_folder)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")



def run_tracking(video_path, coordinates, output_dir):
    global URLid
    global Inpainting_Anything_ModulePath
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
    result = subprocess.run(f"python {Inpainting_Anything_ModulePath}TracktheTarget.py --video_path  {output_dir}\\{str(video_path)} --coordinates {int(coordinates[0])} {int(coordinates[1])} --output_dir {output_dir} --pathPTH {Inpainting_Anything_ModulePath}")

    # Check if the command was executed successfully
    if result.returncode == 0:
        print("Command executed successfully.")
        time.sleep(2)
        forcolmap = os.path.abspath(output_dir+"\\"+URLid+"\\original_frames")
        print (forcolmap)
        
        # run_inpainting(forinpainting,output_dir)
        ColmapObj(forcolmap)
        

        
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
    global Inpainting_Anything_ModulePath
    #print(output_dir)
    jsonFilepath=input_folder+"\\"+URLid+".json"
    colmapjson=input_folder+"\\transform.json"

  
    # Execute the command
    result = subprocess.run(f"python {Inpainting_Anything_ModulePath}MaskAndBk.py --input_img {input_folder} --coordsJson {jsonFilepath} --colmapPath {colmapjson} --point_labels 1 --dilate_kernel_size 15 --output_dir {output_dir} --sam_model_type \"vit_h\" --sam_ckpt {Inpainting_Anything_ModulePath}pretrained_models\\sam_vit_h_4b8939.pth --lama_config {Inpainting_Anything_ModulePath}lama\\configs\\prediction\\default.yaml --lama_ckpt  {Inpainting_Anything_ModulePath}pretrained_models\\big-lama --URID {URLid} ")

    # Check if the command was executed successfully
    if result.returncode == 0:
        print("Command executed successfully.")
        
        time.sleep(2)
        testpath = "./output/"+URLid+"\\"+URLid+"\\original_frames"
        testpath= os.path.abspath(testpath)
        
        BKfolderPath= "./output/"+URLid+"\\"+"GenerateImages\\Bkonly\\images\\"
        
        BKfolderPath=os.path.abspath(BKfolderPath)
        ObjPath=testpath
        NerfObj (colmapjson,ObjPath,"target")
       
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
    global InstantNGP_MoudlePath
    #print(output_dir)
    jsonFilepath=input_folder+"\\transform.json"
    cmd= f"python {InstantNGP_MoudlePath}scripts\\colmap2nerf.py --colmap_matcher exhaustive --run_colmap --aabb_scale 16 --images {input_folder} --out {jsonFilepath} --overwrite"

    # Execute the command
    result = subprocess.run(cmd)

    # Check if the command was executed successfully
    if result.returncode == 0:
        print("Colmap executed successfully.")
        run_inpainting(input_folder,input_folder)
        return jsonFilepath
        # Optional: Print stdout
        
    else:
        print("Command failed with return code", result.returncode)
        return None
        # Print stderr for error
       
def NerfObj (input_json,output_folder,Objtype):
    global URLid
    global InstantNGP_MoudlePath
    
    cmd= f"python {InstantNGP_MoudlePath}scripts\\run.py --training_data {input_json} --save_snapshot {output_folder}\\{URLid}_scaned_{Objtype}.ingp --n_steps 8000 --marching_cubes_density_thresh 2 --marching_cubes_res 128 --save_mesh {output_folder}\\{URLid}_scaned_{Objtype}.obj" 

   # cmd= f"python C:\\Users\\someo\\Desktop\\RealityEditor\\PythonProject\\instant-ngp\\scripts\\colmap2nerf.py --colmap_matcher exhaustive --run_colmap --aabb_scale 16 --images {input_folder}--out {jsonFilepath}"

    # Execute the command
    result = subprocess.run(cmd)


    # Check if the command was executed successfully
    if result.returncode == 0:
        print("Command executed successfully.")
        time.sleep(10)
        
        process_obj_and_save(f"{output_folder}\\{URLid}_scaned_{Objtype}.obj")
       
        # Optional: Print stdout
        
        
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
    # return upload_file_to_server(output_zip)

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
    # return upload_file_to_server(output_zip)
        


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



def load_config(config_file):
    with open(config_file, 'r') as file:
        config = json.load(file)
    return config

        
def oscinit():
    global osc_server
    dispatcherosc = Dispatcher()
    
    
    
    # osc_server = osc_server.ThreadingOSCUDPServer(('10.0.0.123', 6161), dispatcherosc) #Bibi
    

    osc_server = osc_server.ThreadingOSCUDPServer(('192.168.0.139', 6161), dispatcherosc) #JamNET
    # osc_server = osc_server.ThreadingOSCUDPServer(('127.0.0.1', 6161), dispatcherosc)  # Change the IP and port as needed
    # osc_server=osc_server.ThreadingOSCUDPServer(('192.168.137.1', 6161), dispatcherosc) #Laptop Hotspot
    OSCserver_thread = threading.Thread(target=osc_server.serve_forever)
    OSCserver_thread.start()
    print("Serving on {}".format(osc_server.server_address))
   # osc_server.serve_forever()

    dispatcherosc.map("/filter", print)
    dispatcherosc.map("/CreateCropBox", handle_create_crop_box)
    dispatcherosc.set_default_handler(default_handler)
    

def exit_program():
    print("Exiting the program.")
    os.kill(os.getpid(), signal.SIGTERM)

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

    # # Start the OSC server thread
    # osc_thread = threading.Thread(target=start_osc_server)
    # osc_thread.daemon = True
    # osc_thread.start()

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




if __name__ == '__main__':
 
    config_path = './config.json'  # Update this path to where you save your config.json
    config = load_config(config_path)
    Inpainting_Anything_ModulePath = config['Inpainting_Anything_ModulePath']
    InstantNGP_MoudlePath = config['InstantNGP_MoudlePath']
    TexTurePaper_modulePath= config['TEXTurePaper_ModulePath']
    print("Inpainting Module Path:", Inpainting_Anything_ModulePath)
    print("Instant NGP Module Path:", InstantNGP_MoudlePath)
    print("TexttuerePath:",TexTurePaper_modulePath)

    process = subprocess.Popen(["RunServer.bat"], shell=True)
    
    
    
    
    keyboard.add_hotkey('esc', exit_program)
    print("press ESC to exit")

    
    # main_thread = threading.Thread(target=main)
    # main_thread.start()

    #main()

 

    
    try:
         
        oscinit()      
                
    except KeyboardInterrupt:
        exit()
       

    # Wait for the observer thread to finish
  
   
    
    
