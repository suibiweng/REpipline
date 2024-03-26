import time
import os
import zipfile
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from shutil import move
import pymeshlab as ml

def get_timestamp():
    # Get the current date and time
    now = time.localtime()  # Use `time.localtime()` to get the local time

    # Format the date and time as a timestamp string
    timestamp = time.strftime("%Y%m%d%H%M%S", now)
    return timestamp

class Watcher:
    DIRECTORY_TO_WATCH = "G:/My Drive/ModelsTest"  # Replace with the path to the directory you want to watch
    DESTINATION_DIRECTORY = "./FromIPAD"  # Replace with your destination directory path

    def __init__(self):
        self.observer = Observer()

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except:
            self.observer.stop()
            print("Observer Stopped")

        self.observer.join()

class Handler(FileSystemEventHandler):

    @staticmethod
    def zip_file_with_delay(source_folder, file_name, output_zip, delay=3):
        time.sleep(delay)
        file_path = os.path.join(source_folder, file_name)
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, file_name)
        print("Done zipping!")
  
  


    @staticmethod
    def on_any_event(event):
        if event.is_directory:
            return None

        elif event.event_type == 'created':
            # Take any action here when a file is first created.
            print(f"Received created event - {event.src_path}.")
            
            # Create a folder with a timestamp name in ./output
            timestamp = get_timestamp()
            temp_folder_path = os.path.join("./output", timestamp)
            os.makedirs(temp_folder_path, exist_ok=True)
            
            # Move the file into the newly created timestamped folder
            file_name = os.path.basename(event.src_path)
            file_name_with_extension = os.path.basename(event.src_path)
            file_name_without_extension, _ = os.path.splitext(file_name_with_extension)

           
            
            destination_file_path = os.path.join(temp_folder_path, file_name)
            move(event.src_path, destination_file_path)
            
            
           
            print(f"Moved {event.src_path} to {destination_file_path}")
            time.sleep(2)
            # self.fbx_to_obj(destination_file_path, temp_folder_path/timestamp+".obj")
            
            ms = ml.MeshSet()
            ms.load_new_mesh(destination_file_path)
            ms.save_current_mesh(temp_folder_path+"\\"+timestamp+"_target.obj")


            # Define the output zip file name (same name with .zip extension)
            output_zip = os.path.join(Watcher.DESTINATION_DIRECTORY, timestamp + ".zip")
            
            # Zip the file with a delay
            Handler.zip_file_with_delay(temp_folder_path, file_name, output_zip)

if __name__ == '__main__':
    w = Watcher()
    w.run()
