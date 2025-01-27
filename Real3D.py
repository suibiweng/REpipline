import subprocess
import argparse
import os
import zipfile
import time
from datetime import datetime
from pymeshlab import MeshSet
import json
import aspose.threed as a3d

Real3DPath=""


def run_subprocess(input_file, output_dir):
    global Real3DPath
    # Command and arguments
    command = "python"

    script = Real3DPath+"run.py"
    
    checkpointPath= Real3DPath+"checkpoint"

    # Construct the command as a list
    cmd = [command, script, input_file, "--output-dir", output_dir,"--model-save-format", 'glb' , "--pretrained-model-name-or-path",checkpointPath]

    try:
        # Run the command
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Command executed successfully!")
        print("Output:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error while executing the command.")
        print(f"Return Code: {e.returncode}")
        print(f"Output: {e.output}")
        print(f"Error: {e.stderr}")

def is_recently_created(file_path, threshold_seconds=10):
    """Check if a file was created or modified within the last `threshold_seconds`."""
    if not os.path.exists(file_path):
        return False
    file_mod_time = os.path.getmtime(file_path)
    current_time = time.time()
    return current_time - file_mod_time <= threshold_seconds

def convert_glb_to_fbx(glb_path, fbx_path):
    """Convert a .glb file to .fbx using MeshLab Python."""
    try:
        ms = MeshSet()
        ms.load_new_mesh(glb_path)
        ms.save_current_mesh(fbx_path, binary=True)
        print(f"Converted {glb_path} to {fbx_path}")
    except Exception as e:
        print(f"Error converting {glb_path} to {fbx_path}: {e}")


def convert_glb_to_obj_with_textures(glb_path, obj_path):
    """
    Convert a .glb file to .obj with textures using Aspose.3D Python API.

    Args:
        glb_path (str): Path to the input .glb file.
        obj_path (str): Path to save the output .obj file.

    Returns:
        bool: True if conversion is successful, False otherwise.
    """
    if not os.path.exists(glb_path):
        print(f"Error: The input file {glb_path} does not exist.")
        return False

    try:
        # Load the GLB file
        scene = a3d.Scene.from_file(glb_path)

        # Define OBJ save options
        save_options = a3d.ObjSaveOptions()
        save_options.enable_materials = True  # Ensure materials are exported
        save_options.export_textures = True  # Export textures alongside the .obj file
        
        # Get the output directory from the obj_path
        output_dir = os.path.dirname(obj_path)
        
        # Save the .obj file along with its textures and material
        scene.save(obj_path, save_options)
        print(f"Successfully converted {glb_path} to {obj_path} with textures.")
        return True
    except Exception as e:
        print(f"Error during conversion of {glb_path} to {obj_path} with textures: {e}")
        return False

def create_zip_file(file_paths, zip_file_name):
    """Create a zip file containing the specified files in the same folder as the script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    zip_file_path = os.path.join(script_dir, zip_file_name)

    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            if os.path.exists(file_path):
                arcname = os.path.basename(file_path)  # Save only the file name, not the full path
                zipf.write(file_path, arcname)
    print(f"Zipped files into {zip_file_path}")

def load_config(config_file):
    with open(config_file, 'r') as file:
        config = json.load(file)
    return config


if __name__ == "__main__":
    config_path = './config.json'  # Update this path to where you save your config.json
    config = load_config(config_path)
    Real3DPath=config['Real3DPath']


    # Argument parser setup
    parser = argparse.ArgumentParser(description="Process 3D data.")
    parser.add_argument("--input_file", type=str, required=True, help="Path to input file")
    parser.add_argument("--output_dir", type=str, required=True, help="Path to output directory")
    parser.add_argument("--urlid", type=str, required=True, help="Unique URL ID")
    args = parser.parse_args()




    
    # Step 1: Run the initial subprocess
    run_subprocess(args.input_file, args.output_dir)
    
    # Step 2: Locate the generated mesh.glb
    glb_path = os.path.join(args.output_dir+'/0/', "mesh.glb")
    
    if not is_recently_created(glb_path):
        print(f"Error: mesh.glb not found or not recently created in {args.output_dir}")
        exit(1)
    
    # Step 3: Convert mesh.glb to .fbx
    # obj_path = os.path.join(args.output_dir, "mesh.obj")
    # convert_glb_to_obj_with_textures(glb_path, obj_path)
    
    # Step 4: Create a zip file with the converted .fbx in the same directory as this script
    create_zip_file([glb_path], args.urlid+"_reconstruct.zip")
