import os
import shutil

class REFileManager:
    def __init__(self, base_directory="./objects"):
        """Initialize the file manager with a custom base directory."""
        self.base_directory = os.path.abspath(base_directory)  # Get absolute path
        os.makedirs(self.base_directory, exist_ok=True)  # Ensure base directory exists

    def get_folder(self, url_id):
        """Return the folder path for a given URLID, creating it if necessary."""
        folder_path = os.path.join(self.base_directory, url_id)
        os.makedirs(folder_path, exist_ok=True)  # Ensure the folder exists
        return folder_path

    def get_file_path(self, url_id, file_name):
        """Return the full file path with the URLID prefix."""
        folder_path = self.get_folder(url_id)  # Ensures folder exists
        return os.path.join(folder_path, f"{url_id}_{file_name}")

    def list_files(self, url_id):
        """List all files in the given URLID folder."""
        folder_path = self.get_folder(url_id)  # Ensure the folder exists before listing
        return os.listdir(folder_path)  # Return list of file names

    def load_previous_files(self):
        """Load previously saved files from the base directory."""
        previous_files = {}
        if not os.path.exists(self.base_directory):
            return previous_files  # Return empty if base directory does not exist

        for folder in os.listdir(self.base_directory):
            folder_path = os.path.join(self.base_directory, folder)
            if os.path.isdir(folder_path):
                previous_files[folder] = os.listdir(folder_path)  # Store file names per folder
        
        return previous_files  # Returns a dictionary {URLID: [file1, file2, ...]}

    def delete_folder(self, url_id):
        """Delete the folder associated with the URLID."""
        folder_path = os.path.join(self.base_directory, url_id)
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            return True
        return False