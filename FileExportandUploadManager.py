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
from google.cloud import storage

#分享資料
import datetime
import sys
# 上傳檔名 /位置/

theProjectPath=""
ckptPath=r"/ckpt/last.ckpt"
yamalpath=""
stage=0
PngFilePath=None
lastfile=None
private_key_path = '/path/to/your/private/key.pem'
server_ip = '34.106.250.143'
server_port = 22
server_username = 'suibidata2023'
local_file_path = '/path/to/your/local/directory/'  # Replace with your local file path



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
        if event.is_directory:
            return
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
            zip_folder_contents(event.src_path,",model.zip")
            # Handle the case where a folder ending with "export" is created
            print(f"Folder ending with 'export' created: {event.src_path}")
            



class ModelHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.latest_folder = None

    def on_created(self, event):
        if event.is_directory:
            folder_path = event.src_path
            if not self.latest_folder or os.path.getctime(folder_path) > os.path.getctime(self.latest_folder):
                self.latest_folder = folder_path
                zip_folder_contents(self.latest_folder,",model.zip")



def zip_folder_contents(folder_path, output_zip):
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for foldername, subfolders, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)



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

    cmd = f"python launch.py --config {yamalpath} --export --gpu 0 resume={ckptPath} system.exporter_type=mesh-exporter system.exporter.fmt=obj"
    try:
        proc = subprocess.Popen( cmd, shell=True, cwd='C:\\Users\\someo\\Desktop\\RealityEditor\PythonProject\\threestudio')
       
    except Exception as e:
        print("An error occurred:", str(e))

    











# def watch_for_latest_folder(folder_to_watch):
#     global stage
#     global PngFilePath
#     global lastfile
    
#     #lastfile=None
#     event_handler = LatestFolderHandler()
#     png_event = PNGHandler()
#     observer = Observer()
#     observer.schedule(event_handler, folder_to_watch, recursive=False)
#     observer.start()

#     try:
#         while True: #stage != 3
#             if event_handler.latest_folder:
#                 if(lastfile!=event_handler.latest_folder):
#                     lastfile=event_handler.latest_folder
#                     print(event_handler.latest_folder)
                    
#                     if(stage==0):
#                         observer.unschedule_all()  # Stop watching the old folder
#                         observer.schedule(event_handler, lastfile, recursive=False)  # Start watching the new folder
#                         stage=1

#                     elif(stage==1):

#                         print (os.path.basename(event_handler.latest_folder))
#                         if( os.path.basename(event_handler.latest_folder)=='save'):
                            
#                             PngFilePath=event_handler.latest_folder
#                             stage=2
#                             observer.unschedule_all()
#                             observer.schedule(png_event, PngFilePath, recursive=False) 
#                             print("changetoSave")
#                     elif(stage==2):
#                         pass
#                     elif(stage==3):
#                         print("folder to zip and upload it")    
#                 time.sleep(1)
#     except KeyboardInterrupt:
#         observer.stop()
#     observer.join()

getSavePath=False

def PreViewUploader(folder_to_watch):
    global stage
    global PngFilePath
    global lastfile
    global theProjectPath
    global yamalpath
    global ckptPath
    
    
    #lastfile=None
    event_handler = LatestFolderHandler()
    png_event = PNGHandler()
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)
    observer.start()

    try:
        while True: #stage != 3
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
        observer.stop()
    observer.join()
    

# def upload_file(file_name):

#     bucket_name = 'suibidata'
#     # Create a client for interacting with the GCP Storage API, using the ServiceAccount key file
#     client = storage.Client.from_service_account_json('studious-bit-398115-420fcd83daa6.json')
#     # Create a bucket object
#     bucket = client.bucket(bucket_name)
#     # Set the name of the file you want to upload
#     #file_name = 'test2.zip'
#     # Create a blob object from the file
#     blob = bucket.blob( os.path.basename(file_name))
#     # Read the contents of the file
#     with open(file_name, 'rb') as f:
#         contents = f.read()
#     # Upload the file to the bucket
#     blob.upload_from_string(contents)
#     print(f'File { os.path.basename(file_name)} uploaded to {blob.public_url}')
#     # print(f'https://storage.cloud.google.com/suibidata/{file_name}')


#  #分享資料
# def get_presigned_url (bucket_name, blob_name) :
#     # Create a client for interacting with the GCP Storage API, using the ServiceAccount key file
#     client = storage.Client.from_service_account_json('studious-bit-398115-420fcd83daa6.json')
#     # Create a bucket object
#     bucket = client.bucket(bucket_name)

#     blob = bucket.blob(blob_name)
#     url = blob.generate_signed_url(
#         version="v4",
#         # Generate URL for 15 minutes
#         expiration=datetime.timedelta(minutes=15),
#         # Only Allow GET Call.
#         method="GET",
#     )
#     print("Generated GET signed URL:")
#     print(url)
#     return url




if __name__ == "__main__":
    print('')

    folder_to_watch = r"C:\Users\someo\Desktop\RealityEditor\PythonProject\threestudio\outputs\dreamfusion-sd"
    # latest_folder_name = watch_for_latest_folder(folder_to_watch)

    PreviewUPdatethread = threading.Thread(target=PreViewUploader, args=(folder_to_watch,))
    PreviewUPdatethread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("KeyboardInterrupt: Terminating the main program...")
        sys.exit()
        # Perform any cleanup or termination actions here, if needed

    PreviewUPdatethread.join()
    






   # print(f"Latest created folder name: {latest_folder_name}")

    # # The name for the new bucket
    # bucket_name = bucket_name
    # upload_file(bucket_name)
    # # The name for the new bucket
    # bucket_name = bucket_name
    # blob_name = os.path.basename(file_name)
    
    
    # event_handler = PNGHandler()
    # observer = Observer()
    # observer.schedule(event_handler, folder_to_watch, recursive=False)
    # print(f"Watching folder: {folder_to_watch}")
    # observer.start()
    # observer.stop()
    # get_presigned_url(bucket_name, blob_name)
    # print(f'https://storage.cloud.google.com/{bucket_name}/{file_name}')