from flask import Flask, request, jsonify
from PIL import Image, ImageDraw
import os
import rembg
import cv2
import subprocess
import json


app = Flask(__name__)

# Directories for uploads and output
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/upload', methods=['POST'])
def upload_image():
    # Check if 'file' is in the request
    if 'file' not in request.files:
        print("No file part in request")
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    prompt = request.form.get('prompt', 'No prompt provided')
    flip_y = request.form.get('flipY', 'false').lower() == 'true'
    x_offset = int(request.form.get('xOffset', '0'))
    object_position = request.form.get('objectPosition', '(0,0)')
    debug_draw = request.form.get('debugDraw', 'false').lower() == 'true'
    file_type = request.form.get('type', 'default')  # Retrieve the new 'type' field
    urlid = request.form.get('URLID', 'default') 

    # Parse the objectPosition into x, y coordinates
    try:
        object_x, object_y = map(int, object_position.strip("()").split(","))
    except ValueError:
        return jsonify({"error": "Invalid objectPosition format. Use (x,y)"}), 400

    # Check if file has a valid filename
    if file.filename == '':
        print("No selected file")
        return jsonify({"error": "No selected file"}), 400

    # Save the uploaded file
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
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

        # Save the modified image back to the same file path
        image.save(file_path)
    
   
        
        

    except Exception as e:
        print(f"Failed to process image: {e}")
        return jsonify({"error": "Image processing failed"}), 500



    if file_type == "RGB":
        object_position = (object_x,object_y)
        ProccedFile = os.path.join(UPLOAD_FOLDER,urlid+"_rm.png")
        call_removebg_subprocess( file_path, ProccedFile, object_position)


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



def call_Fast3D(input_file,output_dir,zipfile_name):
    # Command and arguments
    command = "python"
    script = "Fast3D.py"
    # input_file = "demo_files/examples/chair1.png"
    # output_dir = "output/"
    # zipfile_name = "output.zip"

    # Construct the command as a list
    cmd = [command, script, input_file, output_dir, zipfile_name]

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
        
        
        
def call_SDimg(server_url, output_file_name, mode, prompt, input_image=None, mask_image=None, 
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
    
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error while calling SDimg.py: {e}")
    except FileNotFoundError:
        print("Make sure SDimg.py exists and is accessible in the current directory.")

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
                "--checkpoint_path","sam_vit_h_4b8939.pth"
            ],
            capture_output=True,
            text=True
        )

        # Handle subprocess results
        if result.returncode == 0:
            print("Subprocess completed successfully!")
            call_Fast3D(output_file,"./output",urlid)
            print(result.stdout)
        else:
            print("Subprocess failed!")
            print(result.stderr)

    except Exception as e:
        print(f"Error calling subprocess: {e}")



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)









# def execute_subprocess(file_path):
#     """
#     Function to execute a subprocess with the specified file,
#     convert resulting .glb to .fbx, and zip the .fbx file.
#     :param file_path: Path to the file to process.
#     :return: Dictionary containing success status, zip path, and error message if any.
#     """
#     try:
#         # Step 1: Run the initial processing script (run.py)
#         subprocess.run(["python", "run.py", file_path, "--output-dir", OUTPUT_FOLDER], check=True)

#         # Assume run.py outputs a .glb file in the output directory
#         glb_file_path = os.path.join(OUTPUT_FOLDER, os.path.splitext(os.path.basename(file_path))[0] + ".glb")
        
#         if not os.path.exists(glb_file_path):
#             return {"success": False, "error": "GLB file not created by run.py"}

#         # Step 2: Convert .glb to .fbx using pymeshlab
#         fbx_file_path = os.path.join(OUTPUT_FOLDER, os.path.splitext(os.path.basename(file_path))[0] + ".fbx")
        
#         # Load the .glb file into a MeshLab workspace
#         ms = pymeshlab.MeshSet()
#         ms.load_new_mesh(glb_file_path)
        
#         # Save the mesh as an .fbx file
#         ms.save_current_mesh(fbx_file_path)

#         if not os.path.exists(fbx_file_path):
#             return {"success": False, "error": "FBX conversion failed"}

#         # Step 3: Zip the .fbx file
#         zip_path = os.path.join(OUTPUT_FOLDER, os.path.splitext(os.path.basename(file_path))[0] + ".zip")
#         with zipfile.ZipFile(zip_path, 'w') as zipf:
#             zipf.write(fbx_file_path, os.path.basename(fbx_file_path))

#         return {"success": True, "zip_path": zip_path}

#     except subprocess.CalledProcessError as e:
#         return {"success": False, "error": str(e)}
#     except Exception as e:
#         return {"success": False, "error": str(e)}
