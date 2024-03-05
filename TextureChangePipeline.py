import time
import yaml
import os
import subprocess
import paramiko
import argparse
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

def create_example_data(exp_name, text, append_direction, shape_path, seed):
    return {
        'log': {
            'exp_name': exp_name
        },
        'guide': {
            'text':f'"{text}"',
            'append_direction': append_direction,
            'shape_path': shape_path
        },
        'optim': {
            'seed': seed
        }
    }
    
def RunTheTRXURE (YamalPath):
    
    result = subprocess.run(f"python -m scripts.run_texture --config_path={YamalPath}")

    # Check if the command was executed successfully
    if result.returncode == 0:
        print("Command executed successfully.")
        time.sleep(2)

        

        
        # Optional: Print stdout
        if result.stdout:
            print("Output:", result.stdout)
        
    else:
        print("Command failed with return code", result.returncode)
        # Print stderr for error
        if result.stderr:
            print("Error:", result.stderr)
    
    return True

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

# class MyHandler(FileSystemEventHandler):
#     def on_created(self, event):
#         if event.is_directory:
#             return

#         print(f"New file created: {event.src_path}")
#         # Extract the file name from the path
#         file_name = event.src_path.split("\\")[-1]

#         # Use the file name in the variables
#         updated_exp_name = file_name.split(".")[0]
#         updated_shape_path = event.src_path
#         print("file name-", updated_exp_name)
#         print("file name-", updated_shape_path)

#         # Create updated example_data with new file name and path
#         updated_example_data = create_example_data(
#             exp_name=updated_exp_name,
#             text='A Wood Cup, {} view',
#             append_direction=True,
#             shape_path=updated_shape_path,
#             seed=3
#         )

#         # Generate YAML
#         yaml_content = generate_yaml(updated_example_data)

#         # Save YAML to a file
#         if yaml_content:
#             save_to_yaml(yaml_content, filename='textures/output.yaml')

def parse_args():
    parser = argparse.ArgumentParser(description="Generate and process a YAML file based on command line arguments.")
    parser.add_argument("--URID", required=True, help="Unique Resource Identifier")
    parser.add_argument("--prompt", required=True, help="Text prompt for guide")
    parser.add_argument("--ShapePath", required=True, help="Path to the shape file")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    # Use arguments from command line
    URID = args.URID
    prompt = args.prompt
    ShapePath = args.ShapePath

    # Your existing logic for processing and generating the YAML
    yamlData = create_example_data(URID, prompt, True, ShapePath, 3)
    yamlfile = save_to_yaml(yamlData, filename='textures/output.yaml')

    
    
    
    

    # event_handler = MyHandler()
    # observer = Observer()
    # observer.schedule(event_handler, path=folder_to_watch, recursive=False)
    # observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        exit()