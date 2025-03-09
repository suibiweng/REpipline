import os
import zipfile
import subprocess
import time
import json
import yaml
import pymeshlab
import argparse

def load_config(config_file):
    """
    Loads a JSON configuration file.
    
    Args:
        config_file (str): The file path to the configuration file.
        
    Returns:
        dict: The configuration data.
    """
    with open(config_file, 'r') as file:
        config = json.load(file)
    return config

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
            'append_direction': True,
            'shape_path': shape_path,
            'text': f"{text},{{}} view"
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

def RunTheTRXURE(config_path, URLid):
    """
    Loads the configuration, executes the texture script, then re-exports the OBJ file and zips the mesh directory.
    
    Args:
        config_path (str): The file path to the JSON configuration file.
        URLid (str): An identifier used to locate experiment directories.
    """
    global TexTurePaper_modulePath
    
    # Load configuration and update module path from the config
    config = load_config(config_path)
    TexTurePaper_modulePath = config['TEXTurePaper_ModulePath']
    print("Loaded configuration. Module path:", TexTurePaper_modulePath)
    
    # Build the command to run the texture script
    cmd = f"python -m scripts.run_texture --config_path={config_path}"
    result = subprocess.run(cmd, cwd=TexTurePaper_modulePath, capture_output=True, text=True)
    
    # Check if the command was executed successfully
    if result.returncode == 0:
        print("Command executed successfully.")
        time.sleep(2)
        
        # Re-export the OBJ file and zip the mesh directory
        mesh_obj_path = os.path.join(TexTurePaper_modulePath, "experiments", URLid, "mesh", "mesh.obj")
        re_export_obj(mesh_obj_path)
        
        mesh_directory = os.path.join(TexTurePaper_modulePath, "experiments", URLid, "mesh")
        output_zip = f"{URLid}_Instruction.zip"
        zip_files_with_delay(mesh_directory, output_zip, delay=10)
        
        if result.stdout:
            print("Output:", result.stdout)
    else:
        print("Command failed with return code:", result.returncode)
        if result.stderr:
            print("Error output:", result.stderr)

def re_export_obj(input_obj_file):
    """
    Re-exports the given OBJ file using a MeshLab server.
    
    Args:
        input_obj_file (str): Path to the OBJ file.
    """
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(input_obj_file)
    ms.save_current_mesh(input_obj_file)
    print("Re-exported OBJ file:", input_obj_file)

def zip_files_with_delay(directory, output_zip, delay=3):
    """
    Zips all files in the specified directory after waiting for a given delay.
    
    Args:
        directory (str): The directory to zip.
        output_zip (str): The name of the output zip file.
        delay (int, optional): Delay in seconds before zipping. Defaults to 3.
    """
    time.sleep(delay)
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, directory)
                zipf.write(file_path, arcname)
    print("Zipping complete. Output file:", output_zip)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run texture process and generate YAML config.")
    parser.add_argument("--config", type=str, default='./config.json', help="Path to the JSON config file")
    parser.add_argument("--urlid", type=str, required=True, help="Experiment identifier")
    parser.add_argument("--output_yaml", type=str, required=True, help="Output YAML file name")
    parser.add_argument("--prompt", type=str, required=True, help="Prompt text for the guide")
    parser.add_argument("--exp_name", type=str, default="TestExperiment", help="Experiment name")
    parser.add_argument("--append_direction", type=str, default="right", help="Append direction")
    parser.add_argument("--shape_path", type=str, default="path/to/shape.obj", help="Path to shape file")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    args = parser.parse_args()
    
    # Save YAML file using the provided arguments
    yaml_file = save_yaml_file(
        exp_name=args.exp_name,
        text=args.prompt,
        append_direction=args.append_direction,
        shape_path=args.shape_path,
        seed=args.seed,
        filename=args.output_yaml
    )
    print("YAML configuration saved to:", yaml_file)
    
    # Run the texture process
    RunTheTRXURE(args.config, args.urlid)
