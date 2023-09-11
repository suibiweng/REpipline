import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import zipfile
import threading

# import packages
from google.cloud import storage

#分享資料
import datetime
import sys
# 上傳檔名 /位置/

ckptPath=r"/ckpt/last.ckpt"
yamalpath=""


stage=0
PngFilePath=None
lastfile=None




class LatestFolderHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.latest_folder = None

    def on_created(self, event):
        if event.is_directory:
            folder_path = event.src_path
            if not self.latest_folder or os.path.getctime(folder_path) > os.path.getctime(self.latest_folder):
                self.latest_folder = folder_path


class PNGHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        # Check if the created file is a PNG file
        if event.src_path.lower().endswith(".png"):
            
            print(f"upload this: {event.src_path}")

class ModelHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.latest_folder = None

    def on_created(self, event):
        if event.is_directory:
            folder_path = event.src_path
            if not self.latest_folder or os.path.getctime(folder_path) > os.path.getctime(self.latest_folder):
                self.latest_folder = folder_path
                zip_folder_contents(self.latest_folder,"obj.zip")



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

    cmd=  f"python launch.py --config {yamalpath} --export --gpu 0 {ckptPath} system.exporter_type=mesh-exporter system.exporter.fmt=obj"
    try:
        proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        on_subprocess_exit(proc)
        if stdout:
            print("Subprocess stdout:", stdout.decode())
        if stderr:
            print("Subprocess stderr:", stderr.decode())
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


def TheModelExporter(folder_to_watch):
    global stage
    global PngFilePath
    global lastfile
    
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
                    print(event_handler.latest_folder)
                    
                    if(stage==0):
                        observer.unschedule_all()  # Stop watching the old folder
                        observer.schedule(event_handler, lastfile, recursive=False)  # Start watching the new folder
                        stage=1

                    elif(stage==1):

                        print (os.path.basename(event_handler.latest_folder))
                        if( os.path.basename(event_handler.latest_folder)=='save'):
                            
                            PngFilePath=event_handler.latest_folder
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


def PreViewUploader(folder_to_watch):
    global stage
    global PngFilePath
    global lastfile
    
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
                    print(event_handler.latest_folder)
                    
                    if(stage==0):
                        observer.unschedule_all()  # Stop watching the old folder
                        observer.schedule(event_handler, lastfile, recursive=False)  # Start watching the new folder
                        stage=1

                    elif(stage==1):

                        print (os.path.basename(event_handler.latest_folder))
                        if( os.path.basename(event_handler.latest_folder)=='save'):
                            
                            PngFilePath=event_handler.latest_folder
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
    

def upload_file(file_name):

    bucket_name = 'suibidata'
    # Create a client for interacting with the GCP Storage API, using the ServiceAccount key file
    client = storage.Client.from_service_account_json('studious-bit-398115-420fcd83daa6.json')
    # Create a bucket object
    bucket = client.bucket(bucket_name)
    # Set the name of the file you want to upload
    #file_name = 'test2.zip'
    # Create a blob object from the file
    blob = bucket.blob( os.path.basename(file_name))
    # Read the contents of the file
    with open(file_name, 'rb') as f:
        contents = f.read()
    # Upload the file to the bucket
    blob.upload_from_string(contents)
    print(f'File { os.path.basename(file_name)} uploaded to {blob.public_url}')
    # print(f'https://storage.cloud.google.com/suibidata/{file_name}')


 #分享資料
def get_presigned_url (bucket_name, blob_name) :
    # Create a client for interacting with the GCP Storage API, using the ServiceAccount key file
    client = storage.Client.from_service_account_json('studious-bit-398115-420fcd83daa6.json')
    # Create a bucket object
    bucket = client.bucket(bucket_name)

    blob = bucket.blob(blob_name)
    url = blob.generate_signed_url(
        version="v4",
        # Generate URL for 15 minutes
        expiration=datetime.timedelta(minutes=15),
        # Only Allow GET Call.
        method="GET",
    )
    print("Generated GET signed URL:")
    print(url)
    return url




if __name__ == "__main__":
    print('')

    folder_to_watch = "D:\Desktop\RealityEditor\output"
    # latest_folder_name = watch_for_latest_folder(folder_to_watch)

    PreviewUPdatethread = threading.Thread(target=PreViewUploader, args=(folder_to_watch,))
    PreviewUPdatethread.start()







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