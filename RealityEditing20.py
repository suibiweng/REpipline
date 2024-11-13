from flask import Flask, request, jsonify
from PIL import Image, ImageDraw
import os
import rembg
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

        # Flip image and adjust object_x for left-to-right flip
        if flip_y:
            # Adjust object_x for horizontal flip
            object_x = width - object_x
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
    
    
    
    
def execute_sam_rembg(point_data, input_file, output_file):
    """
    Executes the rembg command with SAM model and given parameters.

    Args:
        point_data (list): A list of [x, y] coordinates for the SAM prompt.
        input_file (str): The path to the input image file.
        output_file (str): The path to the output image file.

    Returns:
        subprocess.CompletedProcess: The result of the subprocess call.
    """
    # Convert point_data into the required JSON structure
    sam_prompt = [{"type": "point", "data": point_data, "label": 1}]
    sam_prompt_json = json.dumps({"sam_prompt": sam_prompt})

    # Build the command
    command = [
        "rembg", "i", 
        "-m", "sam",
        "-x", sam_prompt_json,
        input_file,
        output_file
    ]

    # Execute the subprocess
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("Command executed successfully:")
        print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print("Error executing command:")
        print(e.stderr)
        return e
    
    
    

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
