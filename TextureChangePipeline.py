import time
import yaml
import json
import os
import subprocess
import paramiko
import argparse
import pymeshlab as ml
import time
import zipfile

URID=""
TexTurePaper_modulePath=""

def generate_yaml(data):
    try:
        yaml_content = yaml.dump(data, default_flow_style=False)
        return yaml_content
    except Exception as e:
        print(f"Error generating YAML: {e}")
        return None

def save_to_yaml(yaml_content, filename='textures/output.yaml'):
    try:
        with open(filename, 'w') as file:
            file.write(yaml_content)
        print(f"YAML saved to {filename}")
        return os.path.abspath(filename)
    except Exception as e:
        print(f"Error saving YAML: {e}")
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
            # 'append_direction': True,
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


def RunTheTRXURE (YamalPath):

    global TexTurePaper_modulePath
    global URID
    cmd= f"python -m scripts.run_texture --config_path={YamalPath}"
    result = subprocess.run(cmd, cwd=TexTurePaper_modulePath, capture_output=True, text=True)

    # Check if the command was executed successfully
    if result.returncode == 0:
        print("Command executed successfully.")
        time.sleep(2)

        

        
        # Optional: Print stdout
        if result.stdout:
            print("Output:", result.stdout)



        
    else:
        print("Command failed with return code", result.returncode)
        re_export_obj(f'.\experiments\{URID}\mesh\mesh.obj')
        zip_files_with_delay(f".\experiments\{URID}\mesh",f"{URID}_Instruction.zip", delay=10)






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
    ms = ml.MeshSet()

    # Load OBJ file
    ms.load_new_mesh(input_obj_file)

    # Export as OBJ (optional: adjust export settings as needed)
    ms.save_current_mesh(input_obj_file)











def upload_file_to_server( local_file_path,server_ip = '34.106.250.143', server_port=22):
   
    
    try:
        # 創建SSH客戶端對象
        ssh = paramiko.SSHClient()

        # 自動添加主機密鑰
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # 使用SSH金鑰進行連接
        ssh.connect(server_ip, port=server_port, username='suibidata2023', key_filename='suibikey.ppk')

        # 創建SFTP客戶端對象
        sftp = ssh.open_sftp()

        # 指定本地文件和遠程文件的路徑
        fileName = local_file_path
        remote_file_path = '/var/www/html/upload/'
        upload_file = remote_file_path + os.path.basename(fileName)

        # 上傳文件
        sftp.put(fileName, upload_file)

        # 關閉SFTP連接
        sftp.close()

        uploaded_url = f'http://{server_ip}/upload/{os.path.basename(fileName)}'  # Construct the uploaded URL
        print(f' {local_file_path} is uploaded {server_ip} at {remote_file_path}。')
        print(f'Download: {uploaded_url}')
        #send_osc_message(VRip, 1337, "/GenrateModel",[modelId,uploaded_url])
        
        return uploaded_url  # Return the uploaded URL as a string
    except Exception as e:
        print(f'Erro：{str(e)}')
        return None  # Return None in case of an error
    finally:
        # 關閉SSH連接
        ssh.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Generate and process a YAML file based on command line arguments.")
    parser.add_argument("--URID", required=True, help="Unique Resource Identifier")
    parser.add_argument("--prompt", required=True, help="Text prompt for guide")
    parser.add_argument("--ShapePath", required=True, help="Path to the shape file")
    parser.add_argument("--ModulePath", required=True, help="Path to the shape file")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    # Use arguments from command line
    URID = args.URID
    prompt = args.prompt
    ShapePath = args.ShapePath
    TexTurePaper_modulePath=args.ModulePath

    # Your existing logic for processing and generating the YAML
  

    yamlfile= save_yaml_file(str(URID), prompt, True, ShapePath, 3, f"./textures/{URID}.yaml")
    #yamlfile = save_to_yaml( yamlData, filename=f'textures/{URID}.yaml')
    print("StartRun Texture pipline")
    RunTheTRXURE (yamlfile)
    
    
    


    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        exit()