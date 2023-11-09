import os
import time
import shutil
import zipfile
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Define the directory to watch and the target directory for moving files
watched_dir = r'C:\Users\someo\Desktop\RealityEditor\PythonProject\dreamgaussian\logs'

# Create a directory for storing the files to be zipped
zip_dir = r'C:\Users\someo\Desktop\RealityEditor\PythonProject\dreamgaussian\logs'

# Define the file extensions you want to watch
extensions = [".mtl", ".obj", ".png"]


# Create a dictionary to store the latest file for each extension
latest_files = {ext: None for ext in extensions}

# Create a class that will handle file system events
class FileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return

        # Get the file extension
        _, ext = os.path.splitext(event.src_path)

        # Check if the extension is in the list of extensions to watch
        if ext in extensions:
            # Check if the file is the latest one for the extension
            if latest_files[ext] is None or os.path.getmtime(event.src_path) > os.path.getmtime(latest_files[ext]):
                latest_files[ext] = event.src_path

# Create an observer to watch the directory
observer = Observer()
event_handler = FileHandler()
observer.schedule(event_handler, path=watched_dir, recursive=False)
observer.start()

try:
    while True:
        time.sleep(5)  # Adjust the sleep interval as needed
        for ext, file_path in latest_files.items():
            if file_path:
                # Create a folder for zipping if it doesn't exist
                os.makedirs(zip_dir, exist_ok=True)
                # Move the files to the zip folder
                shutil.move(file_path, os.path.join(zip_dir, os.path.basename(file_path)))
                latest_files[ext] = None  # Reset the latest file

        # Check if all required files are in the zip folder
        if all(file is not None for file in latest_files.values()):
            # Create a zip file with the three files
            zip_filename = os.path.join(zip_dir, "files.zip")
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for ext, file_path in latest_files.items():
                    zipf.write(file_path, os.path.basename(file_path))

except KeyboardInterrupt:
    observer.stop()
observer.join()
