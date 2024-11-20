import cv2
import numpy as np
import argparse
from matplotlib import pyplot as plt
from matplotlib.widgets import Slider, Button

def apply_focus_blur(rgb_image, depth_normalized, focus_depth, near_blur, far_blur, sensitivity):
    """Applies focus blur based on the given parameters."""
    blurred_image = np.zeros_like(rgb_image)
    for i in range(rgb_image.shape[2]):  # Loop over color channels
        channel = rgb_image[:, :, i]
        blurred_close = cv2.GaussianBlur(channel, (near_blur, near_blur), 0)
        blurred_far = cv2.GaussianBlur(channel, (far_blur, far_blur), 0)
        blending_factor = np.abs(depth_normalized - focus_depth) ** sensitivity
        blending_factor = cv2.normalize(blending_factor, None, 0, 1, cv2.NORM_MINMAX)
        blurred_image[:, :, i] = (blending_factor * blurred_close + (1 - blending_factor) * blurred_far).astype('uint8')
    return blurred_image

def main(rgb_path, depth_path):
    """Main function to load images and run the interactive slider."""
    # Load the input images
    rgb_image = cv2.imread(rgb_path)
    depth_image = cv2.imread(depth_path, cv2.IMREAD_GRAYSCALE)

    if rgb_image is None or depth_image is None:
        raise FileNotFoundError("One or both input files were not found.")

    # Normalize depth image to range 0-1
    depth_normalized = cv2.normalize(depth_image.astype('float32'), None, 0.0, 1.0, cv2.NORM_MINMAX)

    # Calculate the initial focus depth based on the middle of the depth map
    h, w = depth_image.shape
    middle_region = depth_normalized[h // 4: 3 * h // 4, w // 4: 3 * w // 4]
    initial_focus = middle_region.mean()

    # Initial slider values
    initial_near_blur = 5
    initial_far_blur = 25
    initial_sensitivity = 1

    # Create the plot
    fig, ax = plt.subplots()
    plt.subplots_adjust(left=0.25, bottom=0.4)

    # Display the initial image
    blurred_image = apply_focus_blur(rgb_image, depth_normalized, initial_focus, initial_near_blur, initial_far_blur, initial_sensitivity)
    im = ax.imshow(cv2.cvtColor(blurred_image, cv2.COLOR_BGR2RGB))
    ax.set_title("Adjust Focus")
    plt.axis('off')

    # Add sliders
    ax_focus = plt.axes([0.25, 0.3, 0.65, 0.03], facecolor='lightgoldenrodyellow')
    ax_near_blur = plt.axes([0.25, 0.25, 0.65, 0.03], facecolor='lightgoldenrodyellow')
    ax_far_blur = plt.axes([0.25, 0.2, 0.65, 0.03], facecolor='lightgoldenrodyellow')
    ax_sensitivity = plt.axes([0.25, 0.15, 0.65, 0.03], facecolor='lightgoldenrodyellow')

    slider_focus = Slider(ax_focus, 'Focus Depth', 0.0, 1.0, valinit=initial_focus)
    slider_near_blur = Slider(ax_near_blur, 'Near Blur', 1, 15, valinit=initial_near_blur, valstep=2)
    slider_far_blur = Slider(ax_far_blur, 'Far Blur', 15, 35, valinit=initial_far_blur, valstep=2)
    slider_sensitivity = Slider(ax_sensitivity, 'Sensitivity', 0.5, 2.0, valinit=initial_sensitivity)

    # Save button
    ax_save = plt.axes([0.8, 0.05, 0.1, 0.04])
    save_button = Button(ax_save, 'Save')

    # Update function for the sliders
    def update(val):
        focus_depth = slider_focus.val
        near_blur = int(slider_near_blur.val) | 1  # Ensure odd kernel size
        far_blur = int(slider_far_blur.val) | 1    # Ensure odd kernel size
        sensitivity = slider_sensitivity.val
        updated_blur = apply_focus_blur(rgb_image, depth_normalized, focus_depth, near_blur, far_blur, sensitivity)
        im.set_data(cv2.cvtColor(updated_blur, cv2.COLOR_BGR2RGB))
        fig.canvas.draw_idle()

    slider_focus.on_changed(update)
    slider_near_blur.on_changed(update)
    slider_far_blur.on_changed(update)
    slider_sensitivity.on_changed(update)

    # Save function for the button
    def save(event):
        focus_depth = slider_focus.val
        near_blur = int(slider_near_blur.val) | 1  # Ensure odd kernel size
        far_blur = int(slider_far_blur.val) | 1    # Ensure odd kernel size
        sensitivity = slider_sensitivity.val
        save_blurred_image = apply_focus_blur(rgb_image, depth_normalized, focus_depth, near_blur, far_blur, sensitivity)
        save_path = "blurred_image.png"
        cv2.imwrite(save_path, save_blurred_image)
        print(f"Image saved to {save_path}")

    save_button.on_clicked(save)

    plt.show()

# Command-line interface
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive focus blur with default focus on the middle object.")
    parser.add_argument("rgb_image", type=str, help="Path to the RGB image file.")
    parser.add_argument("depth_image", type=str, help="Path to the Depth map image file.")
    args = parser.parse_args()

    main(args.rgb_image, args.depth_image)
