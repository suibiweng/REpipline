from flask import Flask, request, jsonify ,send_from_directory
from PIL import Image, ImageDraw
import os
import cv2
import subprocess
import json
import NDIlib as ndi
import numpy as np
import threading
import requests
import time
import yaml
import zipfile
from REFileManager import REFileManager
import shutil


#from RealityEditorManager import GeneratedModel
# import ShapEserver
import argparse

ndi_frame = None
app = Flask(__name__)

# Directories for uploads and output
UPLOAD_FOLDER = 'uploads'
OBJECTs_FOLDER = 'objects'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OBJECTs_FOLDER, exist_ok=True)


filemanager = REFileManager(base_directory=OBJECTs_FOLDER)

open_ai_key=""

@app.route('/command', methods=['POST'])
def command():
    global filemanager
    command = request.form.get('Command', 'No prompt provided')
    urlid = request.form.get('URLID', 'default')
    prompt = request.form.get('Prompt', '')

    if(urlid!="default"):
        if "@" in urlid:
            parts = urlid.split('@')
            print(parts[0])
            print(parts[1])
            folder=filemanager.get_folder(parts[0]) 
        else:
            folder=filemanager.get_folder(urlid)
        print(urlid)
        print(command)
        print(prompt)

    if command == "IpcamCapture":
        try:
            capture_ipcam_frame(f"{urlid}_IPCAM.png")
            print("IP camera frame captured successfully.")
            call_Fast3D( f"{urlid}_IPCAM.png", "./output", urlid)
            return jsonify({"message": "IP camera frame captured", "file": f"{urlid}_IPCAM.png"}), 200
        except Exception as e:
            print(f"Error capturing IP camera frame: {e}")
            return jsonify({"error": str(e)}), 500
    if command == "ShapeE":
        print(prompt+" "+urlid)
        send_requestShapE(urlid,prompt)
        return jsonify({"message": "ShapeE"}), 200
        # ShapEserver.ShapEgeneratemodel(urlid,prompt)
    if command == "DynamicCoding":
        print("p2play")
        print(prompt)
        print(folder)
        
        call_OpenAI_script(prompt, f"{folder}/{urlid}_DynamicCoding.json",command+"2",urlid)
        return jsonify({"message": "DynamicCodin"}), 200
     
    if command == "ChangeTexture":
         print( urlid+"Change Texture to"+prompt)

         YamalPath=save_yaml_for_Texturefile(urlid, prompt, "append", f"{folder}/{urlid}.obj", 1, f"./textures/{urlid}.yaml")
         RunTheTRXURE (YamalPath,urlid)

         return jsonify({"message": ""}), 200
   

        
        
        
      
    else:
        return jsonify({"error": "Invalid command"}), 400
    



def Geturlid(urlid):
    if "@" in urlid:
        parts = urlid.split('@')
        print(parts[0])
        print(parts[1])
        return parts[0]
    else:
        return urlid




@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    directory_path = "" 
    file_path = os.path.join(directory_path, filename)
    print(f"Requested file: {file_path}")  # Log the file path
    if not os.path.exists(file_path):
        print("File not found!")  # Log if the file does not exist
        return jsonify({"error": "File not found"}), 404

    return send_from_directory(directory_path, filename, as_attachment=True)    
    
        


@app.route('/upload', methods=['POST'])
def upload_image():
    # Check if 'file' is in the request
    #     print("No file part in request")
    #     return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    prompt = request.form.get('prompt', 'No prompt provided')
    flip_y = request.form.get('flipY', 'false').lower() == 'true'
    x_offset = int(request.form.get('xOffset', '0'))
    object_position = request.form.get('objectPosition', '(0,0)')
    debug_draw = request.form.get('debugDraw', 'false').lower() == 'true'
    file_type = request.form.get('type', 'default')  # Retrieve the new 'type' field
    urlid = request.form.get('URLID', 'default') 
    if(urlid!="default"):
        folder=filemanager.get_folder(Geturlid(urlid))
        print(urlid)
   
        print(prompt)
    # Parse the objectPosition into x, y coordinates
    try:
        object_x, object_y = map(int, object_position.strip("()").split(","))
    except ValueError:
        return jsonify({"error": "Invalid objectPosition format. Use (x,y)"}), 400

    # Check if file has a valid filename
    # if file.filename == '':
    #     print("No selected file")
    #     return jsonify({"error": "No selected file"}), 400

    # # Save the uploaded file
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    # if(file_type=="RGB") :
    #     # capture_ndi_window_with_adjusted_contrast(file_path)
    #     #capture_ndi_window_with_contour_enhancement(file_path)
    #     # file.save(file_path)
    #     # capture_ndi_window_with_contrast_and_brightness(file_path)
    #     capture_ndi_window(output_path=file_path)
    # if(file_type=="RGB_modify") :
    #     # capture_ndi_window_with_adjusted_contrast(file_path)
    #     #capture_ndi_window_with_contour_enhancement(file_path)
    #     file.save(file_path)
        # capture_ndi_window_with_contrast_and_brightness(file_path)
        #capture_ndi_window(output_path=file_path)

    if file_type == "Mask" or file_type == "RGB" or file_type=="RGB_modify":
        print(file_type)
        file.save(file_path)
    # Perform the flips, x-offset shift, and debug drawing
        try:
            image = Image.open(file_path).convert("RGBA")
            width, height = image.size  # Get image dimensions
            object_x = width - object_x
            if file_type == "RGB":
                object_x+=30

        # Flip image and adjust object_x for left-to-right flip
            if flip_y:
            # Adjust object_x for horizontal flip
            # Flip the image horizontally and vertically
                image = image.transpose(Image.FLIP_LEFT_RIGHT)
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                print("Image flipped left-to-right, then upside down")
            else:
            # Only flip the image vertically
             
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                print("Image flipped upside down")

        # Draw a red dot at the adjusted objectPosition if debugDraw is true
            if debug_draw:
                draw = ImageDraw.Draw(image)
                dot_radius = 5  # Radius of the red dot
                draw.ellipse(
                [
                    (object_x - dot_radius, object_y - dot_radius),
                    (object_x + dot_radius, object_y + dot_radius)
                ],
                fill=(255, 0, 0, 255)  # Red color
            )
                print(f"Red dot drawn at adjusted position ({object_x}, {object_y})")
            print(f"position ({object_x}, {object_y})")

        # Save the modified image back to the same file path
            
            
            
            image.save(file_path)
            
            if(file_type == "Mask"):
                print(prompt)
               
                offset_image(file_path)
 
                print("shiftMask")
                
          
                rgb = os.path.join(UPLOAD_FOLDER, urlid+"_Modify.png")
                
                image = Image.open(rgb).convert("RGBA")
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                
                image.save(rgb)
                time.sleep(10)
            
                
                call_SDimg(urlid,"http://127.0.0.1:7860", f'{folder}/{urlid}_Modify', "img2img", prompt, input_image=rgb, mask_image=file_path)
                
             
                object_position = (object_x,object_y)
                time.sleep(10)
                print("wait!!!!!")
                #call_Fast3D(f'{urlid}_Modify.png',"./output",urlid)
                call_Real3D(f'{folder}/{urlid}_Modify.png',f"{folder}",urlid)
            #call_Fast3D(file_path, "./output", urlid)
            # ProccedFile = os.path.join(UPLOAD_FOLDER,urlid+"_rm.png")
            # call_removebg_subprocess( f'{urlid}_Modify.png', ProccedFile, object_position,urlid)

        except Exception as e:
              print(f"Failed to process image: {e}")

    if file_type == "RGB":
        object_position = (object_x,object_y)
        ProccedFile = os.path.join(UPLOAD_FOLDER,urlid+"_rm.png")
        #call_Fast3D(file_path, "./output", urlid)
        call_removebg_subprocess( file_path, ProccedFile, object_position,urlid)
    # if file_type == "Mask":
    #     object_position = (object_x,object_y)
    #     rgb = os.path.join(UPLOAD_FOLDER, urlid+".png")
    #     call_SDimg("http://127.0.0.1:7860", f'{urlid}_Modify.png', "img2img", prompt, input_image=rgb, mask_image=file_path)
    # Return the response including all received parameters for reference
    return jsonify({
        "message": "File uploaded and processed successfully",
        "file_path": file_path,
        "prompt": prompt,
        "type": file_type,  # Include the type field in the response
        "flipY": flip_y,
        "xOffset": x_offset,
        "objectPosition": (object_x, object_y),  # Return the modified coordinates
        "debugDraw": debug_draw
    }), 200
def offset_image(image_path, offset_x=45, fill_color=(0, 0, 0)):
    """
    Offsets an image to the right by a given number of pixels and replaces the original image.

    :param image_path: Path to the input image.
    :param offset_x: Number of pixels to shift the image to the right.
    :param fill_color: Color to fill the left gap (default is black).
    """
    # Load image
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Image not found or invalid image path.")

    # Get image dimensions
    height, width, channels = image.shape

    # Create a new blank image with the same shape and fill with the specified color
    offset_img = np.full((height, width, channels), fill_color, dtype=np.uint8)

    # Offset image by shifting pixels
    offset_img[:, offset_x:] = image[:, :-offset_x]

    # Save the modified image, replacing the original one
    cv2.imwrite(image_path, offset_img)

def send_requestShapE(urlid, prompt, url="http://127.0.0.1:6363/generate"):
    data = {
        "URID": urlid,  # Fixed key name (your Flask function expects "URID", not "URLID")
        "prompt": prompt,
        "filename": f"{urlid}_ShapE"
    }
    headers = {"Content-Type": "application/json"}  # Set correct JSON header

    try:
        response = requests.post(url, json=data, headers=headers)  # Use json=data
        print("Response Status Code:", response.status_code)

        # Try to parse JSON response
        try:
            response_json = response.json()
            print("Response JSON:", response_json)
        except requests.exceptions.JSONDecodeError:
            print("Response is not JSON. Raw response:", response.text)

    except requests.RequestException as e:
        print("Error sending request:", e)

def save_lua_from_json(json_path, lua_save_path):
    # Read JSON file
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract object name and Lua code
    object_name = data.get("object", "UnknownObject")
    lua_code = data.get("lua_code", "")

    # Save Lua code to the specified path
    with open(lua_save_path, 'w', encoding='utf-8') as lua_file:
        lua_file.write(lua_code)

    print(f"Object: {object_name}")
    print(f"Lua script saved to: {lua_save_path}")

    return object_name  # Return the object name if needed

def capture_ndi_window_with_contrast_and_brightness(output_path="capture.png", alpha=2.0, beta=-50):
    """
    Capture the current NDI frame, enhance contrast, and lower brightness.
    
    Parameters:
        output_path (str): Path to save the image.
        alpha (float): Contrast adjustment factor (1.0 = no change, >1.0 increases contrast).
        beta (int): Brightness adjustment value (negative to lower brightness, positive to increase).
    """
    global ndi_frame

    if ndi_frame is not None:
        try:
            # Adjust contrast and brightness
            adjusted_frame = cv2.convertScaleAbs(ndi_frame, alpha=alpha, beta=beta)

            # Save the adjusted frame as a PNG image
            cv2.imwrite(output_path, adjusted_frame)
            print(f"NDI window with enhanced contrast and lowered brightness saved to {output_path}")
        except Exception as e:
            print(f"Error capturing NDI window: {e}")
    else:
        print("No NDI frame available to capture.")




def capture_ndi_window_with_contour_enhancement(output_path="capture_contour.png"):
    """
    Capture the current NDI frame, enhance contours, and save the result.
    
    Parameters:
        output_path (str): Path to save the enhanced image.
    """
    global ndi_frame

    if ndi_frame is not None:
        try:
            # Convert to grayscale for edge detection
            gray_frame = cv2.cvtColor(ndi_frame, cv2.COLOR_BGR2GRAY)

            # Apply Canny edge detection
            edges = cv2.Canny(gray_frame, threshold1=50, threshold2=150)

            # Convert edges to a 3-channel image
            edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

            # Blend the edges with the original frame to enhance contours
            enhanced_frame = cv2.addWeighted(ndi_frame, 0.8, edges_colored, 0.5, 0)

            # Save the enhanced frame as a PNG image
            cv2.imwrite(output_path, enhanced_frame)
            print(f"NDI window with enhanced contours saved to {output_path}")
        except Exception as e:
            print(f"Error capturing NDI window: {e}")
    else:
        print("No NDI frame available to capture.")









def adjust_contrast(frame, alpha=1.5, beta=0):
    """
    Adjusts contrast and brightness of the image.
    Alpha: Contrast control [1.0-3.0]
    Beta: Brightness control [0-100]
    """
    return cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)


def capture_ndi_window_with_adjusted_contrast(output_path="capture.png"):
    global ndi_frame

    if ndi_frame is not None:
        try:
            enhanced_frame = adjust_contrast(ndi_frame, alpha=2.0, beta=30)
            cv2.imwrite(output_path, enhanced_frame)
            print(f"NDI window with adjusted contrast saved to {output_path}")
        except Exception as e:
            print(f"Error capturing NDI window: {e}")
    else:
        print("No NDI frame available to capture.")



def capture_ndi_window(output_path="capture.png"):
    global ndi_frame

    if ndi_frame is not None:
        try:
            # Save the current NDI frame as a PNG image
            cv2.imwrite(output_path, ndi_frame)
            print(f"NDI window captured and saved to {output_path}")
        except Exception as e:
            print(f"Error capturing NDI window: {e}")
    else:
        print("No NDI frame available to capture.")



def call_Fast3D(input_file, output_dir, zipfile_name):
    # Command and arguments
    command = "python"
    script = "Fast3D.py"

    # Construct the command as a list with proper flags
    cmd = [
        command,
        script,
        "--input_file", input_file,
        "--output_dir", output_dir,
        "--urlid", zipfile_name
    ]

    try:
        # Run the command
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Subprocess executed successfully!")
        print("Output:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error while executing the subprocess.")
        print(f"Return Code: {e.returncode}")
        print(f"Output: {e.output}")
        print(f"Error: {e.stderr}")
        
        
def call_Real3D(input_file, output_dir, zipfile_name):
    # Command and arguments

    print("Start Real3D")
    command = "python"
    script = "Real3D.py"

    # Construct the command as a list with proper flags
    cmd = [
        command,
        script,
        "--input_file", input_file,
        "--output_dir", output_dir,
        "--urlid", zipfile_name
    ]

    try:
        # Run the command
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Subprocess executed successfully!")
        print("Output:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error while executing the subprocess.")
        print(f"Return Code: {e.returncode}")
        print(f"Output: {e.output}")
        print(f"Error: {e.stderr}")


        
        
        
def call_SDimg(urlid,server_url, output_file_name, mode, prompt, input_image=None, mask_image=None, 
                          seed=1, steps=20, width=512, height=512, cfg_scale=7.0, denoising_strength=0.5):
    """
    Calls the SDimg.py script as a subprocess with the specified arguments.

    Arguments:
    - server_url: URL of the server (e.g., http://127.0.0.1:7862).
    - output_file_name: Base name for the output files.
    - mode: 'txt2img' or 'img2img' to select the API.
    - prompt: Text prompt for the API.
    - input_image: Path to the input image (required for img2img mode).
    - mask_image: Path to the mask image (optional for img2img mode).
    - seed: Seed for the image generation.
    - steps: Number of steps for generation.
    - width: Width of the generated image.
    - height: Height of the generated image.
    - cfg_scale: CFG scale for image generation.
    - denoising_strength: Denoising strength (for img2img mode).
    """
    try:
        # Construct the command
        command = [
            "python", "SDimg.py", 
            "--server_url", server_url,
            "--output_file_name", output_file_name,
            "--mode", mode,
            "--prompt", prompt,
            "--seed", str(seed),
            "--steps", str(steps),
            "--width", str(width),
            "--height", str(height),
            "--cfg_scale", str(cfg_scale)
        ]

        if mode == "img2img":
            if not input_image:
                raise ValueError("input_image is required for img2img mode.")
            command.extend(["--input_image", input_image])
            if mask_image:
                command.extend(["--mask_image", mask_image])
            command.extend(["--denoising_strength", str(denoising_strength)])
        
        # Call the script as a subprocess
        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        # Handle subprocess results
        if result.returncode == 0:
            print("Subprocess completed successfully!_SD")
            print(result.stdout)
            #call_Fast3D(output_file_name,"./output",urlid)
            
        else:
            print("Subprocess failed!")
            print(result.stderr)

    except Exception as e:
        print(f"Error calling subprocess: {e}")
        
        

def generate_3d_model(prompt, urid):
    """
    Calls shap_e_generator.py using subprocess and returns the generated model filename.

    :param prompt: The text prompt to generate the 3D model.
    :param urid: A unique identifier for the model.
    :return: The generated model filename (or error message if the process fails).
    """
    try:
        result = subprocess.run(
            ["python", "shap_e_generator.py", prompt, urid], 
            capture_output=True, 
            text=True,
            check=True  # Raises an exception if the process fails
        )
        return result.stdout.strip()  # Return the output, removing extra spaces/newlines
    except subprocess.CalledProcessError as e:
        return f"Error generating model: {e.stderr.strip()}"
        

# def call_texture_script(urlid, output_yaml_file, prompt, config_path, extra_args=None):
#     """
#     Calls texture_script.py using subprocess with the given parameters.
    
#     Parameters:
#         urlid (str): Experiment identifier.
#         output_yaml_file (str): Name for the output YAML file.
#         prompt (str): Prompt text for the texture process.
#         config_path (str): Path to the JSON configuration file.
#         extra_args (list, optional): Additional command-line arguments as a list.
        
#     Returns:
#         tuple: (stdout, stderr) outputs from the subprocess call.
#     """
#     # Build the command to call texture_script.py
#     command = [
#         "python", "texture_script.py",  # Replace with the actual path if needed
#         "--urlid", urlid,
#         "--output_yaml", output_yaml_file,
#         "--prompt", prompt,
#         "--config", config_path
#     ]
    
#     # Include any extra arguments if provided
#     if extra_args:
#         command.extend(extra_args)
    
#     # Execute the command using subprocess
#     result = subprocess.run(command, capture_output=True, text=True)
    
#     # Print outputs for debugging
#     print("STDOUT:")
#     print(result.stdout)
#     print("STDERR:")
#     print(result.stderr)
    
#     return result.stdout, result.stderr





def call_removebg_subprocess( input_file, output_file, point_data,urlid):
    """
    Calls the removebg script as a subprocess.

    Parameters:
        script_path (str): Path to the `removebg_sam.py` script.
        input_file (str): Path to the input image file.
        output_file (str): Path to save the output image.
        point_data (list): List of two integers representing the point data (e.g., [150, 300]).
        checkpoint_path (str): Path to the SAM model checkpoint.
    """
    try:
        # Convert point_data list to a comma-separated string
        point_data_str = ",".join(map(str, point_data))

        # Call the script as a subprocess
        result = subprocess.run(
            [
                "python", f'removebg_sam.py',
                "--input_file", input_file,
                "--output_file", output_file,
                "--point_data", point_data_str,
                "--checkpoint_path","sam_vit_h_4b8939.pth",
                "--threshold",str(0.2)
            ],
            capture_output=True,
            text=True
        )

        # Handle subprocess results
        if result.returncode == 0:
            print("Subprocess completed successfully!")
            call_Real3D(output_file,"./output",urlid)
            print(result.stdout)
        else:
            print("Subprocess failed!_F3D")
            print(result.stderr)

    except Exception as e:
        print(f"Error calling subprocess: {e}")



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


def NDIShow():
    global ndi_frame

    # Start the NDI receiver thread

    while True:
        if ndi_frame is not None:
            cv2.imshow('NDI Stream', ndi_frame)

        if cv2.waitKey(1) & 0xff == 27:
            break

    cv2.destroyAllWindows()



def flask_server():
    app.run(host='0.0.0.0', port=5000)


def run_server_process():
    subprocess.Popen(["RunServer.bat", "8000"], shell=True)
    subprocess.Popen(["python","ShapEserver.py","6363" ], shell=True)
    #open_the_sd()
    
ipcam_frame = None     
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
                        

                print("Failed to connect to the server, status code:", cap.status_code)
                time.sleep(5)  # Wait before trying to reconnect
        except requests.exceptions.RequestException as e:
            print("Connection error:", e)
            time.sleep(5)  # Wait before trying to reconnect
        except Exception as e:
            print("An unexpected error occurred:", e)
            time.sleep(5)  # Wait before trying to reconnect


def show_ipcam_frame():
    global ipcam_frame

    while True:
        if ipcam_frame is not None:
            cv2.imshow('IP Camera Stream', ipcam_frame)
        
        # Break the loop when the ESC key is pressed
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cv2.destroyAllWindows()
            
def capture_ipcam_frame(output_path="captured_frame.jpg"):
    global ipcam_frame

    if ipcam_frame is not None:
        cv2.imwrite(output_path, ipcam_frame)
        print(f"Frame captured and saved to {output_path}")
    else:
        print("No frame available to capture!")


def call_OpenAI_script(prompt, output_path,instruction,urlid):
    global open_ai_key
    # Construct the command to call the external script
    command = [
        'python', 'send_openai_prompt.py',
        '--prompt', prompt,
        '--output_path', output_path,
        '--instructions_file', f'./PromptInstructions/{instruction}.txt'
    ]
    
    # Run the command using subprocess.Popen
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Communicate with the process to capture stdout and stderr
    stdout, stderr = process.communicate()
    
    # Check the return code for success or error
    if process.returncode == 0:
        print("Success:", stdout)

        if(instruction=="DynamicCoding"):
            shape=""
            shape=save_lua_from_json(output_path,f"{urlid}.lua")
            send_requestShapE(urlid,shape)
        if(instruction=="DynamicCoding2"):
            shape=""
            shape=save_lua_from_json(output_path,f"{urlid}.lua")
            send_requestShapE(urlid,shape)
            #generate_3d_model(shape, urlid)
            #ShapEserver.ShapEgeneratemodel(urlid,shape)




        return True  # Indicate success
    else:
        print("Error:", stderr)
        return False  # Indicate failure

def open_the_sd(sd_folder="sd.webui", batch_file="run.bat"):
    """
    Opens the SD interface by executing the specified batch file using subprocess.Popen.
    
    Parameters:
        sd_folder (str): The folder where the SD batch file is located (default is 'sd.webui').
        batch_file (str): The name of the batch file to run (default is 'run.bat').
    
    Returns:
        int: The return code from the batch file execution.
    """
    # Determine the current script's directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the full path to the batch file
    batch_path = os.path.join(current_dir, "..", sd_folder, batch_file)
    
    try:
        # Start the process using Popen with shell=True for Windows batch file execution
        process = subprocess.Popen(batch_path, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for the process to complete and capture the output and errors
        stdout, stderr = process.communicate()
        
        if stdout:
            print("Output:\n", stdout.decode())
        if stderr:
            print("Errors:\n", stderr.decode())
        
        return process.returncode
    except Exception as e:
        print("Error opening the SD:", e)
        return -1


def load_config(config_file):
    with open(config_file, 'r') as file:
        config = json.load(file)
    return config


def save_yaml_for_Texturefile(exp_name, text, append_direction, shape_path, seed, filename):
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



def RunTheTRXURE (YamalPath,URLid):
    global TexTurePaper_modulePath

    

    # re_export_obj(f'{TexTurePaper_modulePath}\experiments\{URLid}\mesh\mesh.obj')
    # zip_files_with_delay(f"{TexTurePaper_modulePath}\experiments\{URLid}\mesh",f"{URLid}_Instruction.zip", delay=10)

    cmd = ["python", "-m", "scripts.run_texture", f"--config_path={YamalPath}"]

    result = subprocess.Popen(
    cmd,
    cwd=TexTurePaper_modulePath,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
    )

    stdout, stderr = result.communicate()

    # Check if the command was executed successfully
    if result.returncode == 0:
        print("Command executed successfully.")
        time.sleep(2)


        #_in_Project = os.path.join(filemanager.get_folder(args.urlid), f'{args.urlid}.glb') 
        # pathinTexture =f'{TexTurePaper_modulePath}\experiments\{URLid}\mesh\mesh.obj'
        # obj_in_Project = os.path.join(filemanager.get_folder(URLid), f'{URLid}_Texture.obj')
        # shutil.copy(pathinTexture, obj_in_Project)

        source_folder = os.path.join(TexTurePaper_modulePath, 'experiments', URLid, 'mesh')
        destination_folder = os.path.join(filemanager.get_folder(URLid), f'{URLid}_Texture')

# Ensure the destination directory does not already exist
    #     if os.path.exists(destination_folder):
    # shutil.rmtree(destination_folder)  # Remove if it exists to avoid conflicts

# Copy the entire folder and rename it
        shutil.copytree(source_folder, destination_folder)





        zip_files_with_delay(destination_folder,f"{URLid}_Texture.zip", delay=10)

        

        
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

def initialize():
    # ShapEserver.initialize_models()


    return True


if __name__ == '__main__':
    config_path = './config.json'
    config = load_config(config_path)
    open_ai_key = config['open_ai_key']
    TexTurePaper_modulePath=config['TEXTurePaper_ModulePath']
    # TexTurePaper_modulePath="D:\\Desktop\\RealityEditor\\PythonProject\\TEXTurePaper\\"
    run_server_process()
    # initialize()
    # Define arguments
    parser = argparse.ArgumentParser(description="Control which threads to run.")
    parser.add_argument('-ipcam', action='store_true', help="Run IP Camera Receiver thread.")
    parser.add_argument('-ipcamShow', action='store_true', help="Run IP Camera Display thread.")
    parser.add_argument('-ndi', action='store_true', help="Run NDI Receiver thread.")
    parser.add_argument('--ipcam_url', type=str, default="http://192.168.0.60:8001/video_feed",
                        help="URL for the IP camera feed.")
    args = parser.parse_args()

    # Start Flask server thread (always on)
    flask_thread = threading.Thread(target=flask_server)
    flask_thread.daemon = True
    flask_thread.start()

    # Start other threads based on arguments
    if args.ipcam:
        ipcam_thread = threading.Thread(target=ipcam_receiver, args=(args.ipcam_url,))
        ipcam_thread.daemon = True
        ipcam_thread.start()
        ipcamView_thread = threading.Thread(target=show_ipcam_frame)
        ipcamView_thread.daemon = True
        ipcamView_thread.start()


    if args.ndi:
        ndi_thread = threading.Thread(target=ndi_receiver)
        ndi_thread.daemon = True
        ndi_thread.start()
        display_thread = threading.Thread(target=NDIShow)
        display_thread.daemon = True
        display_thread.start()



       
    # Keep the main thread alive
    while True:
        pass