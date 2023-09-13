import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import zipfile
import threading
import paramiko
import shutil
# import packages
import pymeshlab


import keyboard

import datetime
import sys
from pythonosc.udp_client import SimpleUDPClient
import signal
# 上傳檔名 /位置/

VRip='192.168.0.213'
theProjectPath=""
ckptPath=""
yamalpath=""
stage=0
PngFilePath=None
lastfile=None
getSavePath=False
private_key_path = '/path/to/your/private/key.pem'
server_ip = '34.106.250.143'
server_port = 22
server_username = 'suibidata2023'
folder_to_watch = r'D:\Desktop\RealityEditor\PythonProject\threestudio\outputs\dreamfusion-sd'
threeStudioPath= r'D:\Desktop\RealityEditor\PythonProject\threestudio'
ThreadFlag =True

stop_event = threading.Event()

def init():
    
    global theProjectPath,ckptPath,yamalpath,stage,PngFilePath,lastfile,getSavePath,ThreadFlag
    time.sleep(5)
    theProjectPath=""
    ckptPath=""
    yamalpath=""
    stage=0
    PngFilePath=None
    lastfile=None
    getSavePath=False
    ThreadFlag=True
    
    
    


def send_osc_message(ip, port, address, data):
    try:
        client = SimpleUDPClient(ip, port)  # Create client
        client.send_message(address, data)  # Send OSC message
    except Exception as e:
        print(f"Error sending OSC message: {e}")


def find_single_obj_file(folder_path):
    """
    Find and return the full path to the first .obj file found in the specified folder.

    Args:
        folder_path (str): The path to the folder to search for .obj files.

    Returns:
        str or None: The full path to the first .obj file found, or None if no .obj file is found.
    """

    print("find obj in"+folder_path)
    time.sleep(5)
    try:
        # Get a list of all files in the folder
        file_list = os.listdir(folder_path)

        # Find the first .obj file (if any)
        for file in file_list:
            if file.lower().endswith('.obj'):
                return os.path.join(folder_path, file)
    except OSError as e:
        print(f"Error: {e}")

    return None


def save_mesh(loadMeshPath):
    # lines needed to run this specific example
    print("ReSave the Mesh")
   
    output_path = loadMeshPath

    # create a new MeshSet
    ms = pymeshlab.MeshSet()

    # load a new mesh
    ms.load_new_mesh(loadMeshPath)
    
    time.sleep(5)

    # save the current mesh with default parameters
    ms.save_current_mesh(output_path)





def copy_and_rename_png_with_delay(source_file, new_file_name="preview.png", delay_seconds=2):
    """
    Copy a PNG file to the current working directory with the specified new file name
    after a delay and return the destination file path.
    """
    try:
        # Get the current working directory
        current_directory = os.getcwd()

        # Create the destination path by joining the current directory and the new file name
        destination_path = os.path.join(current_directory, new_file_name)

        if not os.path.exists(source_file):
            print(f"Source file '{source_file}' does not exist.")
            return None

        # Delay for the specified number of seconds
        time.sleep(delay_seconds)

        # Copy the source file to the destination with the new name
        shutil.copyfile(source_file, destination_path)

        if os.path.getsize(destination_path) == 0:
            print(f"Copy failed. Destination file '{destination_path}' is 0 bytes.")
            return None

        print(f"File '{source_file}' copied to '{destination_path}' as '{new_file_name}'")

        # Return the destination file path
        return destination_path
    except Exception as e:
        print(f"An error occurred: {e}")
        return None



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
        print(f'文件 {local_file_path} 已成功上傳到伺服器 {server_ip} 的 {remote_file_path}。')
        print(f'下載網址: {uploaded_url}')
        
        return uploaded_url  # Return the uploaded URL as a string
    except Exception as e:
        print(f'上傳文件時出現錯誤：{str(e)}')
        return None  # Return None in case of an error
    finally:
        # 關閉SSH連接
        ssh.close()





class LatestFolderHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.latest_folder = None

    def on_created(self, event):
        global getSavePath
        global PngFilePath
        global ckptPath
        global yamalpath
        
        if event.is_directory:
            folder_path = event.src_path
            if not self.latest_folder or os.path.getctime(folder_path) > os.path.getctime(self.latest_folder):
                self.latest_folder = folder_path
            if  os.path.basename(self.latest_folder)=='save':
                getSavePath=True
                PngFilePath=self.latest_folder
            # if  os.path.basename(self.latest_folder)=='ckpts':
            #     print("ckpt is set")
            #     ckptPath=self.latest_folder+"/last.ckpt"
            # if  os.path.basename(self.latest_folder)=='ckpts':
            #     print("yaml is set")
            #     yamalpath=self.latest_folder+"/parsed.yaml"


class PNGHandler(FileSystemEventHandler):
    def on_created(self, event):
        # Check if the created file is a PNG file
        if event.src_path.lower().endswith(".png"):
            print( event.src_path.lower())
            #uploadPreviewFile
            previewpic=copy_and_rename_png_with_delay(event.src_path.lower())
            upload_file_to_server(previewpic)
            print(f"upload this: {event.src_path.lower()}")
        elif event.src_path.lower().endswith(".mp4"):
            ExportTheModel()
        elif event.is_directory and event.src_path.lower().endswith("export"):
            save_mesh(find_single_obj_file(event.src_path))
            Modelurl= zip_folder_contents_and_upload(event.src_path,"model.zip")
            # Handle the case where a folder ending with "export" is created
            data2 = [0, Modelurl]
            send_osc_message(VRip, 1337, "/GenrateModel", data2)
            restart_preview_updater()
            
            
        





def zip_folder_contents_and_upload(folder_path, output_zip):
    time.sleep(10)
    print("ziping the file")
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for foldername, subfolders, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)
    return upload_file_to_server(output_zip)



def on_subprocess_exit(proc):
    return_code = proc.returncode

    print(f"Subprocess exited with return code {return_code}")

def ZipfolderandUpload(folderPath):
    print("")



def ExportTheModel():
    global yamalpath
    global ckptPath
    global stage
    
    
    time.sleep(3)
    print("export model")
    cmd2= f"python launch.py --config {yamalpath} --export --gpu 0 resume={ckptPath} system.exporter_type=mesh-exporter"
    cmd1 = f"python launch.py --config {yamalpath} --export --gpu 0 resume={ckptPath} system.exporter_type=mesh-exporter system.exporter.fmt=obj"
    try:
        proc = subprocess.Popen( cmd2, shell=True, cwd=threeStudioPath)
       
    except Exception as e:
        print("An error occurred:", str(e))
        restart_preview_updater()

observer = Observer()

def PreViewUploader(folder_to_watch):
    global stage
    global PngFilePath
    global lastfile
    global theProjectPath
    global yamalpath
    global ckptPath
    global ThreadFlag
    global observer
    
    
    #lastfile=None
    event_handler = LatestFolderHandler()
    png_event = PNGHandler()
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)
    observer.start()

    try:
        while  ThreadFlag:

            if event_handler.latest_folder:
                if(lastfile!=event_handler.latest_folder):
                    lastfile=event_handler.latest_folder
        
                    if(stage==0):
                        observer.unschedule_all()  # Stop watching the old folder
                        observer.schedule(event_handler, lastfile, recursive=False)  # Start watching the new folder
                        
                        theProjectPath=event_handler.latest_folder
                        yamalpath="outputs\dreamfusion-sd/"+os.path.basename(theProjectPath)+"\configs\parsed.yaml"
                        ckptPath ="outputs\dreamfusion-sd/"+os.path.basename(theProjectPath)+"\ckpts\last.ckpt"
                        
                        print(theProjectPath)
                        print(yamalpath)
                        print(ckptPath)
                        stage=1

                    elif(stage==1):

                        print (os.path.basename(event_handler.latest_folder))
                        if(getSavePath):
                            print(PngFilePath)
                            stage=2
                            observer.unschedule_all()
                            observer.schedule(png_event, PngFilePath, recursive=False) 
                            print("changetoSave")
                    elif(stage==2):
                        pass
                    elif(stage==3):
                        print("folder to zip and upload it")    
                time.sleep(1)
    except KeyboardInterrupt:
        print("")
    
        observer.stop()
    observer.join()
    


def restart_preview_updater():
   
    global PreviewUPdatethread
    global stage
    global  ThreadFlag
    if PreviewUPdatethread and PreviewUPdatethread.is_alive():
        print("Stopping the PreviewUPdatethread...")
        ThreadFlag=False
        observer.stop()
        
        

   
        #PreviewUPdatethread # You should implement a way to gracefully stop the thread.
        #PreviewUPdatethread.join()
       
    
    time.sleep(3)
    init()
    print("Starting the PreviewUPdatethread again...")
    PreviewUPdatethread = threading.Thread(target=PreViewUploader, args=(folder_to_watch,))

    PreviewUPdatethread.start()
    

def exit_program():
    print("Exiting the program.")
    os.kill(os.getpid(), signal.SIGTERM)     



if __name__ == "__main__":
    print('process is On!')
    







    
    # latest_folder_name = watch_for_latest_folder(folder_to_watch)
    keyboard.add_hotkey('esc',restart_preview_updater)
    PreviewUPdatethread = threading.Thread(target=PreViewUploader, args=(folder_to_watch,))
    PreviewUPdatethread.start()
    
    

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        exit_program()
        print("KeyboardInterrupt: Terminating the main program...")
        ThreadFlag=False
        PreviewUPdatethread.join()
        
        # Perform any cleanup or termination actions here, if needed

   
    