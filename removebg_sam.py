import cv2
import numpy as np
import argparse
import time
import threading
from segment_anything import sam_model_registry, SamPredictor
import torch

# Load SAM model
def load_sam_model(checkpoint_path, model_type="vit_h"):
    # Load SAM model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    sam_model = sam_model_registry[model_type](checkpoint=checkpoint_path)
    sam_model.to(device)  # Move model to GPU
    print(f"Model loaded on: {device}")
    return SamPredictor(sam_model)
# Function to display a loading animation
def loading_animation():
    animation = "|/-\\"
    idx = 0
    start_time = time.time()
    while True:
        elapsed_time = int(time.time() - start_time)
        print(f"\rProcessing... {animation[idx % len(animation)]} {elapsed_time}s elapsed", end="")
        idx += 1
        time.sleep(0.1)

# Background removal function using SAM with transparency
def removebg_with_sam(input_file, output_file, point_data, checkpoint_path, threshold=0.5):
    try:
        # Initialize SAM predictor
        predictor = load_sam_model(checkpoint_path)

        # Load the input image
        img = cv2.imread(input_file, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ValueError(f"Could not read the input file: {input_file}")

        # Convert the image to RGB (SAM works with RGB format)
        if img.shape[-1] == 4:  # Already RGBA
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        else:  # Convert BGR to RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Start the loading animation in a separate thread
        loading_thread = threading.Thread(target=loading_animation, daemon=True)
        loading_thread.start()

        # Set the image in the SAM predictor
        predictor.set_image(img_rgb)

        # Prepare the input point and label (1 = foreground)
        input_points = np.array([point_data])
        input_labels = np.array([1])

        # Predict the mask
        masks, scores, _ = predictor.predict(point_coords=input_points, point_labels=input_labels, multimask_output=True)
        
        print(scores)

        # Filter masks by the threshold
        mask = None
        for i, score in enumerate(scores):
            if score >= threshold:  # Keep masks with confidence >= threshold
                mask = masks[i]
                break

        if mask is None:
            raise ValueError(f"No masks met the confidence threshold of {threshold}.")

        # Apply the mask to create a transparent background
        img_rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)  # Convert to RGBA
        img_rgba[~mask] = (0, 0, 0, 0)  # Set non-mask areas to transparent (RGBA = 0,0,0,0)

        # Save the output image
        cv2.imwrite(output_file, img_rgba)

        # Stop the loading animation
        print("\rProcessing completed in {:.2f}s!".format(time.time() - 0))

    except Exception as e:
        print(f"\nError: {e}")

# Main entry point for CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Background removal using SAM with transparency.")
    parser.add_argument("--input_file", type=str, required=True, help="Path to the input image file.")
    parser.add_argument("--output_file", type=str, required=True, help="Path to save the output image.")
    parser.add_argument("--point_data", type=str, required=True, help="Point data for segmentation (e.g., '150,300').")
    parser.add_argument("--checkpoint_path", type=str, required=True, help="Path to the SAM model checkpoint.")
    parser.add_argument("--threshold", type=float, required=False, default=0.5, help="Confidence threshold for mask selection (default: 0.5).")

    args = parser.parse_args()

    # Parse the point_data argument
    point_data = [int(coord) for coord in args.point_data.split(",")]

    # Call the background removal function, including the threshold
    removebg_with_sam(args.input_file, args.output_file, point_data, args.checkpoint_path, threshold=args.threshold)

