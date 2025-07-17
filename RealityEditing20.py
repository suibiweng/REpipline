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
import glob
from segment_anything import sam_model_registry, SamPredictor
import torch

#from RealityEditorManager import GeneratedModel
# import ShapEserver
import argparse

import datetime
import uuid

class IDGenerator:
    @staticmethod
    def generate_id():
        # Get current date and time
        now = datetime.datetime.now()

        # Format the timestamp: yyyyMMddHHmmss
        timestamp = now.strftime("%Y%m%d%H%M%S")

        # Append a shortened unique identifier (8 characters from UUID)
        unique_id = uuid.uuid4().hex[:8]

        return f"{timestamp}{unique_id}"




ndi_frame = None
app = Flask(__name__)

# Directories for uploads and output
UPLOAD_FOLDER = 'uploads'
OBJECTs_FOLDER = 'objects'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OBJECTs_FOLDER, exist_ok=True)



filemanager = REFileManager(base_directory=OBJECTs_FOLDER)

open_ai_key=""
session_id=""


@app.route('/submit_session', methods=['POST'])
def submit_session():
    try:
        session_data = request.get_json()

        # Make sure the field exists
        session_id = session_data.get("sessionURLID", None)
        if not session_id:
            return jsonify({
                "status": "error",
                "message": "Missing 'sessionURLID' in payload."
            }), 400

        # Save as {sessionURLID}_scene.json
        filename = f"{session_id}_scene.json"
        file_path = os.path.join("", filename)

        with open(file_path, 'w') as f:
            json.dump(session_data, f, indent=2)

        print(f"✅ Saved session to {file_path}")

        return jsonify({
            "status": "success",
            "message": f"Saved as {filename}"
        }), 200

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    

def session_exists(session_id):
    filename = f"{session_id}_scene.json"
    file_path = os.path.join("", filename)
    return os.path.exists(file_path)
    


from flask import send_file

@app.route('/get_session/<session_id>', methods=['GET'])
def get_session(session_id):
    filename = f"{session_id}_scene.json"
    file_path = os.path.join("", filename)

    if os.path.exists(file_path):
        return send_file(file_path, mimetype='application/json')
    else:
        return jsonify({
            "status": "error",
            "message": f"Session '{session_id}' not found."
        }), 404








@app.route('/StoryGenerator', methods=['POST'])
def StoryGenerator():
    StoryText = request.form.get('Story', '')
    urlid = request.form.get('URLID', 'default')
    output_file = f"{urlid}_DreamTeller.json"
    type = request.form.get('type', '')  # Retrieve the new 'type' field

    try:
        print("Story Time!!!")
        # 1. Generate objects using OpenAI script
        if(type=="ChatGPT"):
            call_OpenAI_script(StoryText, output_file, "StoryGenerator", urlid)
           
        elif(type=="Text23D"):
            call_3DTextToPosition_script(StoryText, output_file)
     
        # 2. Load and assign IDs
        with open(output_file, 'r') as f:
            object_list = json.load(f)

        if not isinstance(object_list, list):
            object_list = [object_list]

        for obj in object_list:
            obj["id"] = IDGenerator.generate_id()

        with open(output_file, 'w') as f:
            json.dump(object_list, f, indent=4)

        # 3. Trigger Shap-E generation
        resp = requests.post("http://localhost:6363/generateListofObject", json={"URID": urlid})
        if resp.status_code != 200:
            return jsonify({"error": "Shap-E generation failed", "details": resp.json()}), 500

        return jsonify({"objects": resp.json().get("objects", [])}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500







@app.route('/DrawToModel', methods=['POST'])
def DrawCreate():
    global filemanager
    RGBfile = request.files['file']
    prompt = request.form.get('prompt', 'an object')
    urlid = request.form.get('URLID', 'default')
    object_position = request.form.get('objectPosition', '(0,0)')

    print("DrawTo3D!!!")


    DtD= os.path.join(UPLOAD_FOLDER,urlid+"_D23D.png")
    RGBfile.save(DtD)

    print(urlid)
    folder=filemanager.get_folder(Geturlid(urlid))
    print(folder)

    object_x, object_y = map(int, object_position.strip("()").split(","))
    # object_x-=100
    object_y-=150
    object_position = (object_x,object_y)


    call_SDimg(urlid,"http://127.0.0.1:7860", f'{urlid}_3DDrawing', "img2img", prompt, input_image=DtD)

    time.sleep(10)




    print("wait!!!!!")
    server_url = "http://127.0.0.1:8686/process"
                #call_Fast3D(f'{urlid}_Modify.png',"./output",urlid)
    params = {
                "chunk_size": "49152",
                "mc_resolution": "256",
                "foreground_ratio": "0.65",
                "render": "false",
                "render_num_views": "30",
                "no_remove_bg": "false",
                "zip_filename": f"{urlid}_Drawing.zip",
                "output_folder": f"{folder}",
                "obj_filename": f"{urlid}.obj",
                "glb_filename": f"{urlid}.glb",
                "Object_Point": f"{object_x},{object_y}"
                }

        
    requesttoReal3D(server_url, f'{urlid}_3DDrawing.png', params)
    return jsonify({"message": ""}), 200



@app.route('/command', methods=['POST'])
def command():
    global filemanager
    command = request.form.get('Command', 'No prompt provided')
    urlid = request.form.get('URLID', 'default')
    prompt = request.form.get('Prompt', '')
    version=-1

    if(urlid!="default"):
        if "@" in urlid:
            parts = urlid.split('@')
            print(parts[0])
            print(parts[1])
            version=int(parts[1])
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
        print(urlid)
        if(session_id!=""):

            print("session_id is not empty")
        else:
            print("session_id is empty")
            # session_id = IDGenerator.generate_id()
            # print("New session_id generated:", session_id)
            call_OpenAI_script(prompt, f"{folder}/{urlid}_DynamicCoding.json",command+"2",urlid)


        
        return jsonify({"message": "DynamicCodin"}), 200
     
    if command == "ChangeTexture":
         print( urlid+"Change Texture to"+prompt)
         if(version!=0):
            priviousModelName=get_latest_obj_filename(filemanager.get_folder(Geturlid(urlid)))

         if(urlid=="20250406175338f3a773eeMovie"):
        
            YamalPath="H:\\EditingReality\\REpipline\\textures\\20250406175338f3a773eeMovie.yaml"
         
         else:
           YamalPath=save_yaml_for_Texturefile(Geturlid(urlid), prompt, "append", f"{folder}/{priviousModelName}", 1, f"./textures/{Geturlid(urlid)}.yaml")
        # RunTheTRXURE (YamalPath,urlid)
         url = "http://localhost:7788/start"
         perform_texture_change(url,YamalPath, urlid)

         return jsonify({"message": ""}), 200
   

        
        
        
      
    else:
        return jsonify({"error": "Invalid command"}), 400
    

def get_latest_obj_filename(directory):
    """Returns the name of the latest .obj file in the specified directory."""
    obj_files = glob.glob(os.path.join(directory, "*.obj"))
    if not obj_files:
        return None  # No .obj files found
    latest_file = max(obj_files, key=os.path.getmtime)  # Get the most recently modified file
    return os.path.basename(latest_file)  # Return only the file name# Get the most recently modified file


def Geturlid(urlid):
    if "@" in urlid:
        parts = urlid.split('@')
        print(parts[0])
        print(parts[1])
        return parts[0]
    else:
        return urlid

@app.route('/uploadMesh', methods=['POST'])
def upload_mesh():
    urlid = request.form.get('URLID', 'default') 
    if 'file' not in request.files:
        return jsonify({"status": "fail", "reason": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "fail", "reason": "No filename"}), 400

    file.save(os.path.join(UPLOAD_FOLDER, file.filename))
    print(f"Mesh '{file.filename}' saved successfully!")

    return jsonify({"status": "success", "filename": file.filename}), 200


@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    directory_path = "" 
    file_path = os.path.join(directory_path, filename)
    print(f"Requested file: {file_path}")  # Log the file path
    if not os.path.exists(file_path):
        print("File not found!")  # Log if the file does not exist
        return jsonify({"error": "File not found"}), 404

    return send_from_directory(directory_path, filename, as_attachment=True)

@app.route('/EraseMask', methods=['POST'])
def EraseMaskCreate():
    global filemanager
    RGBfile = request.files['file']
    object_position = request.form.get('objectPosition', '(0,0)')
    urlid = request.form.get('URLID', 'default')
    print(urlid)
    folder=filemanager.get_folder(Geturlid(urlid))
    print(folder)

    object_x, object_y = map(int, object_position.strip("()").split(","))
    object_x+=50
    object_y-=170
    object_position = (object_x,object_y)



    debug = os.path.join(UPLOAD_FOLDER, urlid+"_debug.png")
    mask = os.path.join(UPLOAD_FOLDER, urlid+"_mask.png")
    rgb = os.path.join(UPLOAD_FOLDER, urlid+"_eraseRGB.png")
    ProccedFile= os.path.join(UPLOAD_FOLDER,urlid+"_rm.png")
    RGBfile.save(rgb)

    image = Image.open(rgb).convert("RGBA")


    draw = ImageDraw.Draw(image)
    dot_radius = 5  # Radius of the red dot
    draw.ellipse(
                [
                    (object_x - dot_radius, object_y - dot_radius),
                    (object_x + dot_radius, object_y + dot_radius)
                ],
                fill=(255, 0, 0, 255) 
     ) # Red color
    image.save(debug)





    call_removebg_subprocess(rgb, ProccedFile, object_position,mask,urlid,0.5)
    print(mask)
    print(rgb)
    call_SDimg(urlid,"http://127.0.0.1:7860", f'{urlid}_EraseMask', "img2img", "Remove it", input_image=rgb, mask_image=mask)

    time.sleep(10)

    stdout, stderr = run_depth_export_with_popen(
        r"H:\EditingReality\muggled_dpt\run_depth_export.py",
        f"{urlid}_EraseMask.png",
        device="cuda",
        plane_removal_factor=0.5,
        thresh_min=0.1,
        use_float32=True,
        output_path=f'{urlid}_Remove_depth.png'
    )
    
    print("Standard Output:")
    print(stdout)
    print("Standard Error:")
    print(stderr)

    return jsonify({"message": ""}), 200






    
        


@app.route('/upload', methods=['POST'])
def upload_image():
   
    # Check if 'file' is in the request
    #     print("No file part in request")
    #     return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    msk=request.files.get('mask',None)
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


    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    if file_type == "Depth":
        print(file_type)
        file.save(file_path)


    debug = os.path.join(UPLOAD_FOLDER, urlid+"_debug.png")


    if(msk!= None):
      SegMask = os.path.join(UPLOAD_FOLDER, urlid+"_drawmask.png")
      msk.save(SegMask)
 





    if file_type == "Mask" or file_type == "RGB" or file_type=="RGB_modify":
        print(file_type)
        file.save(file_path)
        print(file_path)
    # Perform the flips, x-offset shift, and debug drawing
        try:
            image = Image.open(file_path).convert("RGBA")
            debug_image = image.copy()
            width, height = image.size  # Get image dimensions
            object_x = width - object_x
            if file_type == "RGB" or file_type == "RGB_modify" or file_type == "Mask":
                #passthrough WebTexture adjectment
                object_x+=145-45
                object_y-=320
                print("offsetPoint")

        # Flip image and adjust object_x for left-to-right flip
            if flip_y:
            # Adjust object_x for horizontal flip
            # Flip the image horizontally and vertically
                image = image.transpose(Image.FLIP_LEFT_RIGHT)
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                print("Image flipped left-to-right, then upside down")
            else:
            # Only flip the image vertically
             
                #image = image.transpose(Image.FLIP_TOP_BOTTOM)
                print("Image flipped upside down")

        # Draw a red dot at the adjusted objectPosition if debugDraw is true
           
            draw = ImageDraw.Draw(debug_image)
            dot_radius = 5  # Radius of the red dot
            draw.ellipse(
                [
                    (object_x - dot_radius, object_y - dot_radius),
                    (object_x + dot_radius, object_y + dot_radius)
                ],
                fill=(255, 0, 0, 255)  # Red color
            )

            debug_image.save(debug)  # Save the debug image with the red dot
                    



            print(f"Red dot drawn at adjusted position ({object_x}, {object_y})")
            print(f"position ({object_x}, {object_y})")
        # Save the modified image back to the same file path
            image.save(file_path)

            # if (file_type == "RGB_modify"):
            # #     # image.save(modified_file_path)
            #     ProccedFile =  modified_file_path
            #     MaskFile = os.path.join(UPLOAD_FOLDER,urlid+"_mask.png")
            #     path = call_removebg_subprocess(file_path, ProccedFile, object_position,MaskFile,urlid)
            #     print(f"Modified image saved as 2 {modified_file_path}")    print("RGB_modify!!!!!!!!")
            #     object_position = (object_x,object_y)
            #     # Save the modified image with a different name
            #     modified_file_path = os.path.join(UPLOAD_FOLDER, f"{urlid}_Modify.png")

            
            


            
            if(file_type == "Mask"):
                print(prompt)
                object_position = (object_x,object_y)
               
                # offset_image(file_path)
 
                print("shiftMask")
                
          
                rgb = os.path.join(UPLOAD_FOLDER, urlid+"_Modify.png")



    
                MaskFile = os.path.join(UPLOAD_FOLDER,urlid+"_Mask.png")
                ProccedFile= os.path.join(UPLOAD_FOLDER,urlid+"_rm.png")
                # path = call_removebg_subprocess(rgb, ProccedFile, object_position,MaskFile,urlid)

                time.sleep(20)


                overlay_mask_on_image(rgb, file_path, rgb)


                make_binary_mask_from_colored_image(file_path, output_path=file_path, threshold=10)






                # img1= crop_image_with_padding(ProccedFile, object_position, crop_size=512, fill_mode='transparent')
                # img1.save(ProccedFile)


                # img2= crop_image_with_padding(file_path, object_position, crop_size=512, fill_mode='transparent')
                # img2.save(file_path)








                
                image = Image.open(rgb).convert("RGBA")
                # image = image.transpose(Image.FLIP_TOP_BOTTOM)
                

                image.save(rgb)
               
            
                
                call_SDimg(urlid,"http://127.0.0.1:7860", f'{urlid}_Modify', "img2img", prompt, input_image=rgb, mask_image=file_path, inpainting_mode= 1)
                
             
               
                time.sleep(10)
                print("wait!!!!!")
                server_url = "http://127.0.0.1:8686/process"
                #call_Fast3D(f'{urlid}_Modify.png',"./output",urlid)
                params = {
                "chunk_size": "49152",
                "mc_resolution": "256",
                "foreground_ratio": "0.65",
                "render": "false",
                "render_num_views": "30",
                "no_remove_bg": "false",
                "zip_filename": f"{urlid}_reconstruct.zip",
                "output_folder": f"{folder}",
                "obj_filename": f"{urlid}.obj",
                "glb_filename": f"{urlid}.glb",
                "Object_Point": f"{object_x},{object_y}"
                }

        
                requesttoReal3D(server_url, f"{urlid}_Modify.png", params)







            #call_Real3D(f'{urlid}_Modify.png',f"{folder}",urlid)
            #call_Fast3D(file_path, "./output", urlid)
            # ProccedFile = os.path.join(UPLOAD_FOLDER,urlid+"_rm.png")
            # call_removebg_subprocess( f'{urlid}_Modify.png', ProccedFile, object_position,urlid)

        except Exception as e:
              print(f"Failed to process image: {e}")
    
    if file_type == "RGB":
        object_position = (object_x,object_y)
        ProccedFile = os.path.join(UPLOAD_FOLDER,urlid+"_rm.png")
        MaskFile = os.path.join(UPLOAD_FOLDER,urlid+"_mask.png")
        # predictor = load_sam_model("sam_vit_h_4b8939.pth")
        # Remove background using SAM with transparency
        if (msk== None):
            path = call_removebg_subprocess(file_path, ProccedFile, object_position,MaskFile,urlid,0.6)
        # ProccedFile=removebg_with_sam(file_path, f"{urlid}_rm.png", object_position)
        else:
            path = apply_mask_and_make_transparent(file_path, SegMask, ProccedFile)


        server_url = "http://127.0.0.1:8686/process"
        image_path = path
        params = {
        "chunk_size": "49152",
        "mc_resolution": "256",
        "foreground_ratio": "0.65",
        "render": "false",
        "render_num_views": "30",
        "no_remove_bg": "false",
        "zip_filename": f"{urlid}_reconstruct.zip",
        "output_folder": f"{folder}",
        "obj_filename": f"{urlid}.obj",
        "glb_filename": f"{urlid}.glb",
        "Object_Point": f"{object_x},{object_y}"
        }

        if(path!=None):
          requesttoReal3D(server_url, image_path, params)
        else:
            print("Error in removebg")


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

from PIL import Image

def make_binary_mask_from_colored_image(image_path, output_path="binary_mask.png", threshold=10):
    """
    Converts a color image with black background into a binary mask:
    - Non-black pixels become white.
    - Black pixels stay black.
    
    Args:
        image_path (str): Path to the input image.
        output_path (str): Where to save the resulting binary mask.
        threshold (int): Black threshold (0–255). Lower means stricter black.
    """
    image = Image.open(image_path).convert("RGB")
    pixels = image.getdata()
    
    mask_pixels = []
    for pixel in pixels:
        r, g, b = pixel
        if r < threshold and g < threshold and b < threshold:
            mask_pixels.append((0, 0, 0))  # Keep black
        else:
            mask_pixels.append((255, 255, 255))  # Turn to white

    binary_mask = Image.new("RGB", image.size)
    binary_mask.putdata(mask_pixels)
    binary_mask.save(output_path)
    print(f"Binary mask saved to {output_path}")



def overlay_mask_on_image(image_path, mask_path, output_path="combined_result.png"):
    """
    Overlays a color+black mask on top of an image, making black parts transparent.
    
    Args:
        image_path (str): Path to the base image.
        mask_path (str): Path to the mask image (color + black).
        output_path (str): Path to save the result image.
    """
    # Load and convert to RGBA
    background = Image.open(image_path).convert("RGBA")
    mask = Image.open(mask_path).convert("RGBA")

    # Resize mask to match background if needed
    if background.size != mask.size:
        mask = mask.resize(background.size)

    # Make black parts in mask transparent
    datas = mask.getdata()
    new_data = []
    for item in datas:
        if item[0] < 10 and item[1] < 10 and item[2] < 10:
            new_data.append((0, 0, 0, 0))  # Transparent
        else:
            new_data.append(item)
    mask.putdata(new_data)

    # Overlay mask on background
    background.paste(mask, (0, 0), mask)
    background.save(output_path)
    print(f"Saved combined image to {output_path}")




def apply_mask_and_make_transparent(rgb_path, mask_path, output_path):
    # Open images
    rgb = Image.open(rgb_path).convert("RGBA")
    mask = Image.open(mask_path).convert("L")  # Convert mask to grayscale

    # Create alpha channel from mask (white=255 opaque, black=0 transparent)
    alpha = mask.point(lambda p: 255 if p > 128 else 0)  # Thresholding
    # Add alpha to RGB image
    r, g, b, _ = rgb.split()
    rgba = Image.merge("RGBA", (r, g, b, alpha))
    # Save result
    rgba.save(output_path)

    return output_path

def run_depth_export_with_popen(script_path, image_path, device="cuda",
                                plane_removal_factor=0.5, thresh_min=0.1,
                                use_float32=True, output_path=None, cwd=None):
    """
    Calls the run_depth_export.py script using subprocess.Popen with the provided parameters.
    
    Parameters:
        script_path (str): Full or relative path to the run_depth_export.py script.
        image_path (str): Path to the input image. If relative, it should be relative to cwd.
        device (str): Device to use (e.g., 'cpu', 'cuda', 'mps'). Default is 'cuda'.
        plane_removal_factor (float): Factor for plane-of-best-fit removal.
        thresh_min (float): Minimum threshold for depth normalization.
        use_float32 (bool): Whether to use 32-bit floating point precision.
        output_path (str): Optional; if provided, specifies the output file path (relative to cwd).
        cwd (str): Optional; working directory to run the subprocess in. If None, uses the caller's cwd.
        
    Returns:
        tuple: (stdout, stderr) captured from the script.
    """
    # Build the command list.
    cmd = [
        "python",
        script_path,
        "-i", image_path,
        "-m",  r"H:\EditingReality\muggled_dpt\model_weights\dpt_beit_large_512.pt",
        "-d", device,
        "--plane_removal_factor", str(plane_removal_factor),
        "--thresh_min", str(thresh_min)
    ]
    
    if use_float32:
        cmd.append("-f32")
        
    if output_path:
        cmd.extend(["--output_path", output_path])
    
    # Use the provided cwd or default to the current working directory.
    if cwd is None:
        cwd = os.getcwd()
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        cwd=cwd
    )
    
    try:
        stdout, stderr = process.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        print("Process timed out.")
    
    return stdout, stderr



def crop_image_with_padding(image_path, center, crop_size=512, fill_mode='black'):
    image = Image.open(image_path)
    x, y = center
    width, height = image.size

    # Ensure image has alpha if using transparency
    if fill_mode == 'transparent':
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        fill_color = (0, 0, 0, 0)  # Transparent
    else:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        fill_color = (0, 0, 0)  # Black

    # Create a new blank image with desired fill
    new_image = Image.new(image.mode, (crop_size, crop_size), fill_color)

    # Calculate box coordinates in original image
    left = x - crop_size // 2
    upper = y - crop_size // 2
    right = left + crop_size
    lower = upper + crop_size

    # Calculate where to paste on the new image
    paste_left = max(0, -left)
    paste_upper = max(0, -upper)

    # Crop area from original image
    crop_box = (
        max(0, left),
        max(0, upper),
        min(right, width),
        min(lower, height)
    )
    cropped_region = image.crop(crop_box)

    # Paste the cropped region into the new image
    new_image.paste(cropped_region, (paste_left, paste_upper))
    return new_image



def offset_image(image_path, offset_x=45, offset_y=-200, fill_color=(0, 0, 0)):
    """
    Offsets an image to the right and down by given numbers of pixels, replacing the original image.

    :param image_path: Path to the input image.
    :param offset_x: Number of pixels to shift the image to the right.
    :param offset_y: Number of pixels to shift the image downward.
    :param fill_color: Color to fill the gaps (default is black).
    """
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Image not found or invalid image path.")

    # Get image dimensions
    height, width, channels = image.shape

    # Create a new blank image with the same dimensions and fill with the specified color
    offset_img = np.full((height, width, channels), fill_color, dtype=np.uint8)

    # Apply both horizontal and vertical offset
    offset_img[offset_y:, offset_x:] = image[:height - offset_y, :width - offset_x]

    # Save the modified image, replacing the original one
    cv2.imwrite(image_path, offset_img)


def requesttoReal3D(server_url: str, image_path: str, params: dict) -> str:
    """
    Sends an image file and additional form parameters to the specified Flask server endpoint,
    then saves the returned ZIP file in the same folder as this client script.
    
    Args:
        server_url (str): The URL of the /process endpoint (e.g., "http://localhost:5000/process").
        image_path (str): Path to the image file.
        params (dict): A dictionary of form parameters (e.g., "zip_filename", etc.).

    Returns:
        str: The full path where the ZIP file was saved.
    """
    with open(image_path, "rb") as image_file:
        files = {"image": image_file}
        response = requests.post(server_url, data=params, files=files)
    
    if response.status_code == 200:
        # Save the ZIP file in the same folder as this script.
        script_dir = os.path.dirname(os.path.abspath(__file__))
        zip_filename = params.get("zip_filename", "output.zip")
        save_path = os.path.join(script_dir, zip_filename)
        with open(save_path, "wb") as f:
            f.write(response.content)
        return save_path
    else:
        raise Exception(f"Request failed: {response.status_code} {response.text}")



def send_requestShapE(urlid, prompt, url="http://127.0.0.1:6363/generate"):
    data = {
        "URID": urlid,  # Fixed key name (your Flask function expects "URID", not "URLID")
        "prompt": prompt,
        "filename": f"{urlid}"
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
                          seed=1, steps=20, width=512, height=512, cfg_scale=7.0, denoising_strength=0.5,inpainting_mode=1):
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
            "--cfg_scale", str(cfg_scale),
            "--inpainting_mode", str(inpainting_mode)
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
        

def perform_texture_change(url, yaml_path: str, URLid: str) -> None:
    global filemanager
    global TexTurePaper_modulePath

    # Send POST request to the Flask server.
    payload = {"yaml_path": yaml_path}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return

    print("Server response:", result)
    
    # Check if the response indicates success.
    if "status" in result:
        # Build source and destination paths.
        source_folder = os.path.join(TexTurePaper_modulePath, 'experiments', Geturlid(URLid), 'mesh')
        destination_folder = os.path.join(filemanager.get_folder(Geturlid(URLid)), f'{Geturlid(URLid)}_Texture')
        
        poll_interval = 5  # seconds between checks
        print("Waiting for the source folder to be ready...")
        while True:
            if os.path.exists(source_folder) and os.path.isdir(source_folder):
                # Check if the folder is not empty.
                if os.listdir(source_folder):
                    print("Source folder is ready.")
                    break
            print("Source folder not ready. Waiting...")
            time.sleep(poll_interval)
        
        print(f"Copying from {source_folder} to {destination_folder}...")
        shutil.copytree(source_folder, destination_folder)
        print("Copy completed. Zipping folder after delay...")
        
        zip_files_with_delay(destination_folder, f"{URLid}_Texture.zip", delay=5)
        print("Post-success operations completed.")
    else:
        print("Texture change request failed. No post-success operations executed.")



# Load SAM model
def load_sam_model(checkpoint_path, model_type="vit_h"):
    # Load SAM model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    sam_model = sam_model_registry[model_type](checkpoint=checkpoint_path)
    sam_model.to(device)  # Move model to GPU
    print(f"Model loaded on: {device}")
    return SamPredictor(sam_model)
# Function to display a loading animation
def loading_animation():
    animation = "|/-\\"
    idx = 0
    start_time = time.time()
    while True:
        elapsed_time = int(time.time() - start_time)
        print(f"\rProcessing... {animation[idx % len(animation)]} {elapsed_time}s elapsed", end="")
        idx += 1
        time.sleep(0.1)

# Background removal function using SAM with transparency

def removebg_with_sam(input_file, output_file, point_data, threshold=0.5):
    """
    Loads the SAM model, performs segmentation using the given point,
    saves the output image (with background removed) and then releases memory.
    
    Parameters:
      - input_file: Path to the input image.
      - output_file: Path where the output image will be saved.
      - point_data: A tuple or list representing a single point (e.g. [x, y]).
      - threshold: Confidence threshold for selecting a mask.
      
    Returns the output_file path if successful, otherwise None.
    """
    try:
        # Load predictor every time this function is called.
        predictor = load_sam_model("sam_vit_h_4b8939.pth")
        
        # Read the input image
        img = cv2.imread(input_file, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ValueError(f"Could not read the input file: {input_file}")
        
        # Convert image to RGB for SAM (SAM expects RGB input)
        if img.shape[-1] == 4:
            # If already 4 channels, assume BGRA; convert to BGR then to RGB.
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        else:
            # For a 3-channel image, convert from BGR to RGB.
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Set the image for the predictor.
        predictor.set_image(img_rgb)
        
        # Prepare point and label data. SAM expects point coordinates in [x, y] order.
        input_points = np.array([point_data])
        input_labels = np.array([1])
        
        # Get segmentation masks.
        masks, scores, _ = predictor.predict(
            point_coords=input_points, 
            point_labels=input_labels, 
            multimask_output=True
        )
        
        # Select a mask that meets the confidence threshold.
        mask = None
        for i, score in enumerate(scores):
            if score >= threshold:
                mask = masks[i]
                break
        
        if mask is None:
            raise ValueError(f"No masks met the confidence threshold of {threshold}.")
        
        # Prepare an RGBA image for output.
        # If the original image is 3-channel, convert to BGRA.
        if img.shape[-1] == 3:
            img_rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        elif img.shape[-1] == 4:
            # If already 4-channel, copy it.
            img_rgba = img.copy()
        else:
            raise ValueError("Unsupported number of channels in input image.")
        
        # Create a uint8 mask and apply it: set pixels to transparent (0,0,0,0) where mask == 0.
        mask_uint8 = (mask * 255).astype(np.uint8)
        img_rgba[mask_uint8 == 0] = (0, 0, 0, 0)
        
        # Write the output image.
        if not cv2.imwrite(output_file, img_rgba):
            raise IOError(f"Failed to write image to {output_file}")
        print(f"Output saved to: {output_file}")
        
        # Release predictor memory.
        predictor.set_image(None)
        del predictor
        torch.cuda.empty_cache()
        
        return output_file

    except Exception as e:
        print(f"\nError: {e}")
        return None


def call_removebg_subprocess( input_file, output_file, point_data,mask_file,urlid, threshold=0.2):
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
                "--output_mask", mask_file,
                "--checkpoint_path","sam_vit_h_4b8939.pth",
                "--threshold",str(0.2)
            ],
            capture_output=True,
            text=True
        )

        # Handle subprocess results
        if result.returncode == 0:
            print("Subprocess completed successfully!")
            return output_file
            print(result.stdout)
        else:
            print("Subprocess failed!_F3D")
            print(result.stderr)
            return None

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
    #subprocess.Popen(["python","ShapEserver.py","6363" ], shell=True)
    # open_the_sd()
    
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




def call_OpenAI_script(prompt, output_path, instruction, urlid):
    command = [
        'python', 'send_openai_prompt.py',
        '--prompt', prompt,
        '--output_path', output_path,
        '--instructions_file', f'./PromptInstructions/{instruction}.txt'
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()

    if process.returncode == 0:
        print("Success:", stdout)
       

        if not os.path.exists(output_path):
            raise FileNotFoundError(f"[OpenAI Script] Output file not found: {output_path}")
        

    # Optional: post-processing if needed
        if instruction in ["DynamicCoding", "DynamicCoding2"]:

            print("After call OPENAI:" + urlid)
            shape = save_lua_from_json(output_path, f"{urlid}.lua")
            send_requestShapE(urlid, shape)

    return True


def call_3DTextToPosition_script( sentence,output_path,model_path="model_final.pth"):
    command = [
        'python', '3DTextToPosition.py',
        '--model_path', model_path,
        '--sentence', sentence,
        '--output_path', output_path
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()

    if process.returncode == 0:
        print("Success:", stdout)

        if not os.path.exists(output_path):
            raise FileNotFoundError(f"[3DTextToPosition Script] Output file not found: {output_path}")

    else:
        print("Error:", stderr)
        raise RuntimeError(f"[3DTextToPosition Script] Failed with error:\n{stderr}")

    return True







# def call_OpenAI_script(prompt, output_path,instruction,urlid):
#     global open_ai_key
#     # Construct the command to call the external script
#     command = [
#         'python', 'send_openai_prompt.py',
#         '--prompt', prompt,
#         '--output_path', output_path,
#         '--instructions_file', f'./PromptInstructions/{instruction}.txt'
#     ]
    
#     # Run the command using subprocess.Popen
#     process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
#     # Communicate with the process to capture stdout and stderr
#     stdout, stderr = process.communicate()
    
#     # Check the return code for success or error
#     if process.returncode == 0:
#         print("Success:", stdout)

#         if(instruction=="DynamicCoding"):
#             shape=""
#             shape=save_lua_from_json(output_path,f"{urlid}.lua")
#             send_requestShapE(urlid,shape)
#         if(instruction=="DynamicCoding2"):
#             shape=""
#             shape=save_lua_from_json(output_path,f"{urlid}.lua")
#             send_requestShapE(urlid,shape)
#             #generate_3d_model(shape, urlid)
#             #ShapEserver.ShapEgeneratemodel(urlid,shape)




#         return True  # Indicate success
#     else:
#         print("Error:", stderr)
#         return False  # Indicate failure

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
            'exp_name': exp_name,
            'log_images' : False
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
    print("TextureStart!!")

    

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

        source_folder = os.path.join(TexTurePaper_modulePath, 'experiments', Geturlid(URLid), 'mesh')
        destination_folder = os.path.join(filemanager.get_folder(Geturlid(URLid)), f'{Geturlid(URLid)}_Texture')
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

import tempfile
def zip_files_with_delay(directory, output_zip, delay=10):
    time.sleep(delay)

    # Create a temporary file to hold the zip
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        temp_zip_path = tmp.name

    try:
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, directory)
                    zipf.write(file_path, arcname)

        # After successful zipping, move to final destination
        shutil.move(temp_zip_path, output_zip)
        print("Done!")

    except Exception as e:
        # If anything fails, clean up the temp file
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
        raise e

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

    # predictor = load_sam_model("sam_vit_h_4b8939.pth")
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