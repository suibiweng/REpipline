import torch
import subprocess
from flask import Flask, jsonify, request, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import pymeshlab
import zipfile
from shap_e.diffusion.sample import sample_latents
from shap_e.diffusion.gaussian_diffusion import diffusion_from_config
from shap_e.models.download import load_model, load_config
from shap_e.util.notebooks import decode_latent_mesh
import sys
import tempfile
import shutil
from REFileManager import REFileManager

Real3DPath = ""
filemanager = REFileManager()

# Initialize Flask
app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app)

# Model loading function
def load_models():
    """Loads models dynamically only when needed."""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")  # Debugging
    xm = load_model('transmitter', device=device)
    model = load_model('text300M', device=device)
    diffusion = diffusion_from_config(load_config('diffusion'))
    return xm, model, diffusion, device

def free_memory():
    """Clears GPU memory after processing to avoid memory buildup."""
    torch.cuda.empty_cache()
    torch.cuda.ipc_collect()

def Geturlid(urlid):
    if "@" in urlid:
        parts = urlid.split('@')
        return parts[0]
    return urlid

@app.route("/generate", methods=["POST"])
def generate_model():
    data = request.json
    urid = data.get("URID")
    prompt = data.get("prompt")
    filename = data.get("filename")

    if not urid or not prompt or not filename:
        return jsonify({"error": "Missing URID, prompt, or filename"}), 400

    # Load models only when needed
    xm, model, diffusion, device = load_models()

    try:
        result = generate(prompt, 24, 60, 'obj', filename, urid, xm, model, diffusion, device)
        return jsonify({"message": result, "zip_file": f"{urid}_ShapE.zip"})
    finally:
        # Unload models and free memory
        del xm, model, diffusion
        free_memory()

def generate(prompt, cfg, steps, fileFormat, filename, urlid, xm, model, diffusion, device):
    with torch.no_grad():  # Reduce memory usage
        latents = sample_latents(
            batch_size=1,
            model=model,
            diffusion=diffusion,
            guidance_scale=int(cfg),
            model_kwargs=dict(texts=[prompt]),
            progress=True,
            clip_denoised=True,
            use_fp16=True,  # Use lower precision
            use_karras=True,
            karras_steps=int(steps),
            sigma_min=1E-3,
            sigma_max=160,
            s_churn=0,
        )

        for i, latent in enumerate(latents):
            t = decode_latent_mesh(xm, latent).tri_mesh()
            with open(f'plyFile.ply', 'wb') as f:
                t.write_ply(f)

        export_file('plyFile.ply', f'{filename}.{fileFormat}', fileFormat, urlid)

def export_file(input_file, output_file, output_format, urlid):
    global filemanager
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(input_file)

    # Check if vertex colors exist before proceeding
    if not ms.current_mesh().has_vertex_color():
        print("Warning: Mesh does not have vertex colors!")

    # Define export options to preserve vertex colors
    export_options = {
        "save_vertex_color": True,
        "save_face_color": True,
        "save_wedge_texcoord": True
    }

    if output_format in ["ply", "glb", "gltf"]:
        ms.save_current_mesh(output_file, **export_options)
    elif output_format == "obj":
        ms.save_current_mesh(output_file, save_vertex_color=True)
    elif output_format == "fbx":
        ms.save_current_mesh(output_file, **export_options)
    else:
        print("Invalid output file format.")

    # Copy file to project path
    project_path = filemanager.get_folder(Geturlid(urlid)) + f"/{urlid}_ShapE.{output_format}"
    shutil.copyfile(output_file, project_path)

    # Ensure the file was saved before zipping
    if os.path.exists(output_file):
        temp_zip_path = tempfile.NamedTemporaryFile(delete=False, suffix=".zip").name
        final_zip_path = f"{urlid}_ShapE.zip"

        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(output_file, os.path.basename(output_file))

        # Rename temp zip file to the final zip name after zipping is complete
        shutil.move(temp_zip_path, final_zip_path)
        print(f"Zipped the file successfully: {final_zip_path}")
    else:
        print(f"Error: {output_file} was not saved successfully.")

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    directory_path = "./"
    file_path = os.path.join(directory_path, filename)

    print(f"Requested file: {file_path}")  # Log the file path

    if not os.path.exists(file_path):
        print("File not found!")  # Log if the file does not exist
        return jsonify({"error": "File not found"}), 404

    return send_from_directory(directory_path, filename, as_attachment=True)

if __name__ == '__main__':
    port = 6363
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Invalid port number. Using default 6363.")
    
    app.run(debug=False, host='0.0.0.0', port=port)
