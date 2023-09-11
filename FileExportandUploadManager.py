import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# import packages
from google.cloud import storage

#分享資料
import datetime
import sys
# 上傳檔名 /位置/


class LatestFolderHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.latest_folder = None

    def on_created(self, event):
        if event.is_directory:
            folder_path = event.src_path
            if not self.latest_folder or os.path.getctime(folder_path) > os.path.getctime(self.latest_folder):
                self.latest_folder = folder_path


def watch_for_latest_folder(folder_to_watch):
    event_handler = LatestFolderHandler()
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)
    observer.start()

    try:
        while True:
            if event_handler.latest_folder:
                return event_handler.latest_folder
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    


class PNGHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        # Check if the created file is a PNG file
        if event.src_path.lower().endswith(".png"):
            # Replace this line with your desired action
            print(f"New PNG file created: {event.src_path}")



file_name = 'test3.zip'
bucket_name = 'suibidata'
def upload_file(bucket_name):
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


folder_to_watch = "/path/to/your/folder"

if __name__ == "__main__":
    print('')
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