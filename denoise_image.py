import cv2
import numpy as np
import matplotlib.pyplot as plt
import argparse

def denoise_image(input_image_path, output_image_path=None, show_image=False):
    """
    Denoises an image using Non-Local Means Denoising.

    :param input_image_path: Path to the input image.
    :param output_image_path: Path to save the denoised image (optional).
    :param show_image: Whether to display the image (default is False).
    """
    # Load the image
    img = cv2.imread(input_image_path)
    
    if img is None:
        print("Error: Image not found or the path is incorrect.")
        return

    # Convert image to RGB (OpenCV loads images in BGR by default)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Apply Non-Local Means Denoising
    denoised_img = cv2.fastNlMeansDenoisingColored(
        src=img_rgb,
        h=15,  # Filter strength for luminance
        templateWindowSize=7,
        searchWindowSize=21
    )

    # Save the denoised image if an output path is provided
    if output_image_path:
        denoised_img_bgr = cv2.cvtColor(denoised_img, cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_image_path, denoised_img_bgr)

    # Display the original and denoised images if required
    if show_image:
        plt.figure(figsize=(10, 5))
        plt.subplot(1, 2, 1)
        plt.title("Original Image")
        plt.imshow(img_rgb)
        plt.axis("off")

        plt.subplot(1, 2, 2)
        plt.title("Denoised Image")
        plt.imshow(denoised_img)
        plt.axis("off")

        plt.show()

    print("Denoising completed.")
    if output_image_path:
        print(f"Denoised image saved at: {output_image_path}")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Denoise an image using Non-Local Means Denoising.")
    parser.add_argument("input_image", type=str, help="Path to the input noisy image.")
    parser.add_argument("-o", "--output_image", type=str, default=None, help="Path to save the denoised image.")
    parser.add_argument("-s", "--show", action="store_true", help="Display the original and denoised images.")
    
    args = parser.parse_args()

    # Call the denoise function with the parsed arguments
    denoise_image(args.input_image, args.output_image, args.show)
