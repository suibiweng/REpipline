import cv2
import numpy as np
import argparse

def generate_ambient_occlusion(depth_map, kernel_size=5, gradient_scale=2.0, depth_scale=1.0):
    """
    Generate an ambient occlusion map from a depth map with enhanced edge darkness.
    
    Args:
        depth_map (numpy.ndarray): Grayscale depth map.
        kernel_size (int): Size of Gaussian blur for depth smoothing.
        gradient_scale (float): Scaling factor to amplify gradient magnitude.
        depth_scale (float): Scaling factor for depth normalization.
    
    Returns:
        numpy.ndarray: Enhanced AO map.
    """
    # Normalize the depth map with scaling
    depth_map_normalized = cv2.normalize(depth_map, None, 0, depth_scale, cv2.NORM_MINMAX)
    
    # Invert the depth map to simulate occlusion (closer objects occlude more)
    depth_map_inverted = 1 - depth_map_normalized
    
    # Apply a blur to simulate light diffusion (optional)
    depth_blur = cv2.GaussianBlur(depth_map_inverted, (kernel_size, kernel_size), 0)
    
    # Compute the gradients to detect edges
    sobel_x = cv2.Sobel(depth_blur, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(depth_blur, cv2.CV_64F, 0, 1, ksize=3)
    gradient_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
    
    # Amplify gradients and normalize
    amplified_gradient = gradient_magnitude * gradient_scale
    ao_map = 1 - cv2.normalize(amplified_gradient, None, 0, 1, cv2.NORM_MINMAX)
    
    # Convert AO map to 8-bit grayscale
    return (ao_map * 255).astype(np.uint8)

def visualize_with_slider(depth_map_path, rgb_image_path):
    """
    Open a visualization window with sliders to adjust AO intensity and depth scaling, and a button to save the image.
    """
    # Load images
    depth_map = cv2.imread(depth_map_path, cv2.IMREAD_GRAYSCALE)
    rgb_image = cv2.imread(rgb_image_path)

    if depth_map is None or rgb_image is None:
        raise ValueError("Error loading input images. Check the file paths.")
    
    # Initial values for sliders
    kernel_size = 5
    gradient_scale = 2.0
    depth_scale = 1.0
    blended_image = None

    # Callback function for the trackbars
    def update_visualization(_):
        nonlocal blended_image
        # Get slider values
        gradient_scale = cv2.getTrackbarPos("Gradient Scale", "AO Map") / 10.0
        depth_scale = cv2.getTrackbarPos("Depth Scale", "AO Map") / 10.0
        threshold = cv2.getTrackbarPos("AO Threshold", "AO Map")

        # Generate AO map
        ao_map = generate_ambient_occlusion(depth_map, kernel_size, gradient_scale, depth_scale)

        # Apply threshold to AO map
        ao_adjusted = cv2.threshold(ao_map, threshold, 255, cv2.THRESH_BINARY_INV)[1]

        # Create a 3-channel AO map
        ao_3channel = cv2.merge([ao_adjusted] * 3)

        # Blend AO with RGB image
        blended_image = cv2.addWeighted(rgb_image, 0.7, ao_3channel, 0.3, 0)

        # Display updates
        cv2.imshow("AO Map", ao_adjusted)
        cv2.imshow("Blended RGB + AO", blended_image)

    # Initialize windows
    cv2.namedWindow("AO Map")
    cv2.namedWindow("Blended RGB + AO")
    cv2.createTrackbar("AO Threshold", "AO Map", 128, 255, update_visualization)
    cv2.createTrackbar("Gradient Scale", "AO Map", int(gradient_scale * 10), 50, update_visualization)
    cv2.createTrackbar("Depth Scale", "AO Map", int(depth_scale * 10), 50, update_visualization)

    # Initial display
    update_visualization(0)

    # Save button listener
    while True:
        key = cv2.waitKey(1) & 0xFF

        if key == ord('s'):  # Press 's' to save the images
            if blended_image is not None:
                output_path_rgb = "adjusted_image_with_ao.png"
                ao_output_path = "adjusted_ao_map.png"
                cv2.imwrite(output_path_rgb, blended_image)
                cv2.imwrite(ao_output_path, ao_map)
                print(f"Blended image saved as '{output_path_rgb}'")
                print(f"AO map saved as '{ao_output_path}'")
            else:
                print("No blended image to save!")
        
        elif key == 27:  # Press 'Esc' to exit
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Argument parser setup
    parser = argparse.ArgumentParser(description="Visualize and adjust ambient occlusion with a depth map and RGB image.")
    parser.add_argument("--input_depth", required=True, help="Path to the input depth map image (grayscale).")
    parser.add_argument("--input_rgb", required=True, help="Path to the input RGB image.")
    args = parser.parse_args()

    # Call the visualization function
    visualize_with_slider(args.input_depth, args.input_rgb)
