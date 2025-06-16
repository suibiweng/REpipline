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
import json
from threading import Lock

# Global lock to prevent concurrent Shap-E jobs
generation_lock = Lock()

Real3DPath = ""
filemanager = REFileManager()

# Initialize Flask
app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app)


# Model loading function
def load_models():
    try:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {device}")

        print("[Model Load] Loading transmitter...")
        xm = load_model('transmitter', device=device)
        print("[Model Load] Transmitter loaded.")

        print("[Model Load] Loading text300M...")
        model = load_model('text300M', device=device)
        print("[Model Load] text300M loaded.")

        print("[Model Load] Loading diffusion config...")
        config = load_config('diffusion')
        diffusion = diffusion_from_config(config)
        print("[Model Load] Diffusion config loaded.")

        return xm, model, diffusion, device

    except Exception as e:
        print(f"[Model Load Error] {e}")
        raise


def free_memory():
    """Clears GPU memory after processing to avoid memory buildup."""
    torch.cuda.empty_cache()
    torch.cuda.ipc_collect()

def Geturlid(urlid):
    if "@" in urlid:
        parts = urlid.split('@')
        return parts[0]
    return urlid
import socket
def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"[IP ERROR] {e}")
        return "127.0.0.1"

@app.route("/generateListofObject", methods=["POST"])
def generate_list_of_objects():
    xm = model = diffusion = device = None  # Initialize to prevent UnboundLocalError

    if not generation_lock.acquire(timeout=10):
        print("[LOCK] Generation already in progress. Rejecting new request.")
        return jsonify({"error": "Shap-E server is currently busy. Try again shortly."}), 429

    data = request.json
    urlid = data.get("URID")
    if not urlid:
        generation_lock.release()
        return jsonify({"error": "Missing URID"}), 400

    json_path = f"{urlid}_DreamTeller.json"
    if not os.path.exists(json_path):
        generation_lock.release()
        return jsonify({"error": f"{json_path} not found"}), 404

    try:
        with open(json_path, 'r') as f:
            object_list = json.load(f)

        if not isinstance(object_list, list):
            object_list = [object_list]

        # Load models once
        xm, model, diffusion, device = load_models()
        server_ip = get_local_ip()

        for obj in object_list:
            name = obj["name"]
            obj_id = obj["id"]

            print(f"[Shap-E] Generating: {name} (ID: {obj_id})")

            generate(
                prompt=name,
                cfg=24,
                steps=60,
                fileFormat='obj',
                filename=obj_id,
                urlid=urlid,
                xm=xm,
                model=model,
                diffusion=diffusion,
                device=device
            )

            obj["url"] = f"http://{server_ip}:8000/{obj_id}_shapE.zip"

        with open(json_path, 'w') as f:
            json.dump(object_list, f, indent=4)

        ready_path = json_path.replace(".json", "_Ready.json")
        os.rename(json_path, ready_path)
        print(f"[Shap-E] Done. Renamed to: {ready_path}")

        return jsonify({
            "message": "All models generated successfully",
            "objects": object_list
        })

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        # Safe deletion
        for var_name in ['xm', 'model', 'diffusion']:
            if var_name in locals():
                del locals()[var_name]
        free_memory()
        generation_lock.release()



@app.route("/generate", methods=["POST"])
def generate_model():
    data = request.json
    urid = data.get("URID")
    prompt = data.get("prompt")
    filename = data.get("filename")  # should be the object's ID

    if not urid or not prompt or not filename:
        return jsonify({"error": "Missing URID, prompt, or filename"}), 400

    xm, model, diffusion, device = load_models()

    try:
        generate(prompt, 24, 60, 'obj', filename, urid, xm, model, diffusion, device)

        return jsonify({
            "message": "Generation complete.",
            "zip_file": f"{filename}_shapE.zip"
        })

    finally:
        del xm, model, diffusion
        free_memory()
   

def generate(prompt, cfg, steps, fileFormat, filename, urlid, xm, model, diffusion, device):
    with torch.no_grad():
        latents = sample_latents(
            batch_size=1,
            model=model,
            diffusion=diffusion,
            guidance_scale=int(cfg),
            model_kwargs=dict(texts=[prompt]),
            progress=True,
            clip_denoised=True,
            use_fp16=True,
            use_karras=True,
            karras_steps=int(steps),
            sigma_min=1E-3,
            sigma_max=160,
            s_churn=0,
        )

        for i, latent in enumerate(latents):
            t = decode_latent_mesh(xm, latent).tri_mesh()
            with open('plyFile.ply', 'wb') as f:
                t.write_ply(f)

        # 🔧 Pass filename explicitly
        export_file('plyFile.ply', f'{filename}.{fileFormat}', fileFormat, urlid, filename)


def export_file(input_file, output_file, output_format, urlid, filename):
    global filemanager
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(input_file)

    if not ms.current_mesh().has_vertex_color():
        print("Warning: Mesh does not have vertex colors!")

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

    # Save to project path (can keep this for reference)
    project_path = filemanager.get_folder(Geturlid(urlid)) + f"/{filename}.{output_format}"
    shutil.copyfile(output_file, project_path)

    if os.path.exists(output_file):
        temp_zip_path = tempfile.NamedTemporaryFile(delete=False, suffix=".zip").name
        final_zip_path = f"{filename}_shapE.zip"  # ✅ Use filename (id) for ZIP

        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(output_file, os.path.basename(output_file))

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
