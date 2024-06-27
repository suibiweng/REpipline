import cv2
import numpy as np
import json
from tkinter import *
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import os
import NDIlib as ndi

# Global variables to hold the current images for saving
current_left_image = None
current_right_image = None
current_disparity_image = None


def update_values():
    global stereo
    stereo.setBlockSize(slider_blockSize.get())
    stereo.setNumDisparities(slider_numDisparities.get() * 16)
    stereo.setPreFilterCap(slider_preFilterCap.get())
    stereo.setUniquenessRatio(slider_uniquenessRatio.get())
    stereo.setSpeckleWindowSize(slider_speckleWindowSize.get())
    stereo.setSpeckleRange(slider_speckleRange.get())
    stereo.setDisp12MaxDiff(slider_disp12MaxDiff.get())
    stereo.setP1(8 * 3 * slider_blockSize.get() ** 2)
    stereo.setP2(32 * 3 * slider_blockSize.get() ** 2)

def save_parameters():
    params = {
        'numDisparities': slider_numDisparities.get(),
        'blockSize': slider_blockSize.get(),
        'preFilterCap': slider_preFilterCap.get(),
        'uniquenessRatio': slider_uniquenessRatio.get(),
        'speckleWindowSize': slider_speckleWindowSize.get(),
        'speckleRange': slider_speckleRange.get(),
        'disp12MaxDiff': slider_disp12MaxDiff.get()
    }
    with open('stereo_params.json', 'w') as f:
        json.dump(params, f)
    print("Parameters saved")

def load_parameters():
    filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if not filepath:
        return
    with open(filepath, 'r') as f:
        params = json.load(f)
    slider_numDisparities.set(params['numDisparities'])
    slider_blockSize.set(params['blockSize'])
    slider_preFilterCap.set(params['preFilterCap'])
    slider_uniquenessRatio.set(params['uniquenessRatio'])
    slider_speckleWindowSize.set(params['speckleWindowSize'])
    slider_speckleRange.set(params['speckleRange'])
    slider_disp12MaxDiff.set(params['disp12MaxDiff'])
    update_values()
    print("Parameters loaded")

def save_capture():
    global current_left_image, current_right_image, current_disparity_image
    if current_left_image is not None and current_right_image is not None and current_disparity_image is not None:
        cv2.imwrite('left_image.png', cv2.cvtColor(np.array(current_left_image), cv2.COLOR_RGB2BGR))
        cv2.imwrite('right_image.png', cv2.cvtColor(np.array(current_right_image), cv2.COLOR_RGB2BGR))
        cv2.imwrite('depth_map.png', np.array(current_disparity_image))
        print("Images saved successfully.")

def process_frame():
    global current_left_image, current_right_image, current_disparity_image
    video_frame = ndi.VideoFrameV2()
    if ndi.recv_capture_v2(recv_instance, video_frame, None, None, 5000) == ndi.RECV_STATUS_FRAME_READY:
        frame = np.copy(video_frame.data)
        height, width, _ = frame.shape
        mid_point = width // 2
        frame_left = frame[:, :mid_point, :]
        frame_right = frame[:, mid_point:, :]
        gray_left = cv2.cvtColor(frame_left, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(frame_right, cv2.COLOR_BGR2GRAY)

        disparity = stereo.compute(gray_left, gray_right).astype(np.float32)
        disparity = (disparity - disparity.min()) / (disparity.max() - disparity.min()) * 255
        disparity = np.uint8(disparity)

        # Convert to PIL format and update the GUI
        current_left_image = Image.fromarray(frame_left)
        current_right_image = Image.fromarray(frame_right)
        current_disparity_image = Image.fromarray(disparity)

        left_photo = ImageTk.PhotoImage(image=current_left_image)
        right_photo = ImageTk.PhotoImage(image=current_right_image)
        disparity_photo = ImageTk.PhotoImage(image=current_disparity_image)

        # Update the image in the GUI
        label_left.config(image=left_photo)
        label_left.image = left_photo
        label_right.config(image=right_photo)
        label_right.image = right_photo
        label_disparity.config(image=disparity_photo)
        label_disparity.image = disparity_photo

    root.after(10, process_frame)

# Initialize NDI
if not ndi.initialize():
    print("Cannot run NDI.")
    exit(0)

find_instance = ndi.find_create_v2()
sources = ndi.find_get_current_sources(find_instance)

recv_create = ndi.RecvCreateV3()
recv_create.source_to_connect_to = sources[0]
recv_create.color_format = ndi.RECV_COLOR_FORMAT_BGRX_BGRA
recv_instance = ndi.recv_create_v3(recv_create)

if recv_instance is None:
    print("Error creating NDI receiver")
    exit(0)

ndi.find_destroy(find_instance)

# Initialize GUI
root = Tk()
root.title("StereoSGBM Parameter Adjustment")

frame_images = Frame(root)
frame_images.grid(column=0, row=0, sticky=(N, W, E, S))

frame_controls = Frame(root)
frame_controls.grid(column=1, row=0, sticky=(N, W, E, S))

label_left = Label(frame_images)
label_left.grid(column=0, row=0, sticky=(N, W, E, S))

label_right = Label(frame_images)
label_right.grid(column=1, row=0, sticky=(N, W, E, S))

label_disparity = Label(frame_images)
label_disparity.grid(column=2, row=0, sticky=(N, W, E, S))

# Sliders for SGBM parameters
slider_numDisparities = Scale(frame_controls, from_=1, to=18, label="Num Disparities (/16)", orient=HORIZONTAL, command=lambda x: update_values())
slider_numDisparities.set(3)
slider_numDisparities.grid(column=0, row=0)

slider_blockSize = Scale(frame_controls, from_=5, to_=21, label="Block Size", orient=HORIZONTAL, command=lambda x: update_values())
slider_blockSize.set(5)
slider_blockSize.grid(column=0, row=1)

slider_preFilterCap = Scale(frame_controls, from_=5, to_=63, label="Pre Filter Cap", orient=HORIZONTAL, command=lambda x: update_values())
slider_preFilterCap.set(63)
slider_preFilterCap.grid(column=0, row=2)

slider_uniquenessRatio = Scale(frame_controls, from_=5, to_=15, label="Uniqueness Ratio", orient=HORIZONTAL, command=lambda x: update_values())
slider_uniquenessRatio.set(10)
slider_uniquenessRatio.grid(column=0, row=3)

slider_speckleWindowSize = Scale(frame_controls, from_=50, to_=200, label="Speckle Window Size", orient=HORIZONTAL, command=lambda x: update_values())
slider_speckleWindowSize.set(100)
slider_speckleWindowSize.grid(column=0, row=4)

slider_speckleRange = Scale(frame_controls, from_=16, to_=64, label="Speckle Range", orient=HORIZONTAL, command=lambda x: update_values())
slider_speckleRange.set(32)
slider_speckleRange.grid(column=0, row=5)

slider_disp12MaxDiff = Scale(frame_controls, from_=0, to_=25, label="Disp12 Max Diff", orient=HORIZONTAL, command=lambda x: update_values())
slider_disp12MaxDiff.set(1)
slider_disp12MaxDiff.grid(column=0, row=6)

button_save = Button(frame_controls, text="Save", command=save_parameters)
button_save.grid(column=0, row=7, pady=4)

button_load = Button(frame_controls, text="Load", command=load_parameters)
button_load.grid(column=0, row=8, pady=4)

# Resolution Combobox


button_save_capture = Button(frame_controls, text="Save Capture", command=save_capture)
button_save_capture.grid(column=0, row=10, pady=4)

update_values()  # Set initial values
process_frame()  # Start the video processing

root.mainloop()

# Release NDI resources
ndi.recv_destroy(recv_instance)
ndi.destroy()
cv2.destroyAllWindows()
