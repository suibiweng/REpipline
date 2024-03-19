import shutil

def move_file(source, destination):
    try:
        shutil.move(source, destination)
        print(f"File moved successfully from {source} to {destination}")
    except Exception as e:
        print(f"Error: {e}")

# Example usage
source_file = "G:\\My Drive\\ModelsTest\\Scaniverse 2024-03-19 003031.fbx"
destination_folder = "./"
move_file(source_file, destination_folder)