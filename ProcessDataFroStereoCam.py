import os
import sys
from PIL import Image

def split_and_save_images_in_folder(folder_path):
    try:
        # Create a folder named "Tonerf" within the target folder
        output_folder = os.path.join(folder_path, 'Tonerf')
        os.makedirs(output_folder, exist_ok=True)
        
        # Get all files in the folder
        files = os.listdir(folder_path)
        
        # Filter images
        image_files = [file for file in files if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]

        for image_file in image_files:
            image_path = os.path.join(folder_path, image_file)
            # Open the image
            with Image.open(image_path) as img:
                # Get the dimensions of the image
                width, height = img.size

                # Calculate the midpoint
                mid = width // 2

                # Split the image
                left_half = img.crop((0, 0, mid, height))
                right_half = img.crop((mid, 0, width, height))

                # Save the halves into the "Tonerf" folder
                left_half.save(os.path.join(output_folder, 'left_half_' + image_file))
                right_half.save(os.path.join(output_folder, 'right_half_' + image_file))

        print("Images split and saved successfully.")
    except Exception as e:
        print("An error occurred:", e)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_path>")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    if not os.path.isdir(folder_path):
        print("Error: Invalid folder path.")
        sys.exit(1)
    
    split_and_save_images_in_folder(folder_path)