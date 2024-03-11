import time
import os
import shutil
import zipfile
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import paramiko
from pythonosc.udp_client import SimpleUDPClient
from pythonosc.dispatcher import Dispatcher
from pythonosc.udp_client import SimpleUDPClient
from pythonosc import osc_server

MovingisDone=False
FolderPath=""
VRip='192.168.0.213'




class MyHandler(FileSystemEventHandler):
    def __init__(self):
        self.latest_files = []

    def on_created(self, event):
        if event.is_directory:
            return

        new_file = event.src_path

        if any(new_file.endswith(ext) for ext in (".obj", ".mtl", ".png")):
            self.latest_files.append(new_file)

        # Keep only the latest three files
        if len(self.latest_files) > 3:
            self.latest_files.pop(0)

        print(f"New file created: {new_file}")
        print(f"Latest files: {self.latest_files}")

        if len(self.latest_files) == 3:
            self.handle_latest_files()

    def handle_latest_files(self):
        global MovingisDone
        global FolderPath
        
        timestamp = time.strftime("%Y%m%d%H%M%S")
        obj_folder_name = f"Folder_{timestamp}"
        obj_folder_path = os.path.join(os.path.dirname(self.latest_files[0]), obj_folder_name)

        if not os.path.exists(obj_folder_path):
            os.mkdir(obj_folder_path)

        # Move the latest three files to the folder
        
        time.sleep(10)
        
        for file_to_move in self.latest_files:
            destination_path = os.path.join(obj_folder_path, os.path.basename(file_to_move))
            shutil.move(file_to_move, destination_path)
            print(f"Moved {os.path.basename(file_to_move)} to {obj_folder_name}")

        # Clear the list of latest files after moving
        self.latest_files.clear()
        FolderPath=obj_folder_path
        MovingisDone=True

        # Uncomment the line below if you want to zip the folder after clearing the list
        # zip_folder_with_delay(obj_folder_path, os.path.join(obj_folder_path, "model.zip"))


def send_osc_message(ip, port, address, data):
    try:
        client = SimpleUDPClient(ip, port)  # Create client
        client.send_message(address, data)  # Send OSC message
    except Exception as e:
        print(f"Error sending OSC message: {e}")

def zip_folder_with_delay(folder_path, output_zip, delay=3):
    time.sleep(delay)
    global MovingisDone
    global FolderPath
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        
        for foldername, subfolders, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)
        FolderPath=""
        MovingisDone=False
        print("Done!")
 
    return upload_file_to_server(output_zip)
        



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
        send_osc_message(VRip, 1337, "/GenrateModel", uploaded_url)
        
        return uploaded_url  # Return the uploaded URL as a string
    except Exception as e:
        print(f'上傳文件時出現錯誤：{str(e)}')
        return None  # Return None in case of an error
    finally:
        # 關閉SSH連接
        ssh.close()


def initialize_observer(path, event_handler):
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=False)

    # Start the observer in a separate thread
    observer_thread = threading.Thread(target=observer.start)
    observer_thread.start()

    return observer, observer_thread

if __name__ == "__main__":
    path_to_watch_files = 'C:/Users/someo/Desktop/RealityEditor/PythonProject/dreamgaussian/logs'
    event_handler_files = MyHandler()

    observer_files, observer_thread_files = initialize_observer(path_to_watch_files, event_handler_files)

    try:
        while True:
            time.sleep(1)
            if(MovingisDone):
                print("start Zip")
                zip_folder_with_delay(FolderPath, "model.zip")
                
                
                
    except KeyboardInterrupt:
        observer_files.stop()

    # Wait for the observer thread to finish
    observer_thread_files.join()
