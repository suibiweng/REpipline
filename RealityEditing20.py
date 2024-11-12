from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Directories for uploads and output
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output2'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_image():
    # Check if a file part is present in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    prompt = request.form.get('prompt', 'No prompt provided')

    # Check if the uploaded file has a filename
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the uploaded file
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    return jsonify({"message": "File uploaded successfully", "file_path": file_path, "prompt": prompt}), 200

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
