from flask import Flask, request, jsonify
from PIL import Image, ImageDraw
import os
import rembg
import cv2
import subprocess
import json
import NDIlib as ndi
import numpy as np
import threading
import requests
import time

ndi_frame = None
app = Flask(__name__)

# Directories for uploads and output
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/upload', methods=['POST'])
def upload_image():
    # Check if 'file' is in the request
    #     print("No file part in request")
    #     return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    prompt = request.form.get('prompt', 'No prompt provided')
    flip_y = request.form.get('flipY', 'false').lower() == 'true'
    x_offset = int(request.form.get('xOffset', '0'))
    object_position = request.form.get('objectPosition', '(0,0)')
    debug_draw = request.form.get('debugDraw', 'false').lower() == 'true'
    file_type = request.form.get('type', 'default')  # Retrieve the new 'type' field
    urlid = request.form.get('URLID', 'default') 

    # Parse the objectPosition into x, y coordinates
    try:
        object_x, object_y = map(int, object_position.strip("()").split(","))
    except ValueError:
        return jsonify({"error": "Invalid objectPosition format. Use (x,y)"}), 400

    # Check if file has a valid filename
    # if file.filename == '':
    #     print("No selected file")
    #     return jsonify({"error": "No selected file"}), 400
    print(prompt)
    # # Save the uploaded file
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    if(file_type=="RGB") :
        # capture_ndi_window_with_adjusted_contrast(file_path)
        #capture_ndi_window_with_contour_enhancement(file_path)
        # file.save(file_path)
        # capture_ndi_window_with_contrast_and_brightness(file_path)
        capture_ndi_window(output_path=file_path)
    else: 
        file.save(file_path)
    

    if file_type == "Mask":
    # Perform the flips, x-offset shift, and debug drawing
        try:
            image = Image.open(file_path).convert("RGBA")
            width, height = image.size  # Get image dimensions
            object_x = width - object_x
            if file_type == "RGB":
                object_x+=30

        # Flip image and adjust object_x for left-to-right flip
            if flip_y:
            # Adjust object_x for horizontal flip
            # Flip the image horizontally and vertically
                image = image.transpose(Image.FLIP_LEFT_RIGHT)
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                print("Image flipped left-to-right, then upside down")
            else:
            # Only flip the image vertically
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                print("Image flipped upside down")

        # Draw a red dot at the adjusted objectPosition if debugDraw is true
            if debug_draw:
                draw = ImageDraw.Draw(image)
                dot_radius = 5  # Radius of the red dot
                draw.ellipse(
                [
                    (object_x - dot_radius, object_y - dot_radius),
                    (object_x + dot_radius, object_y + dot_radius)
                ],
                fill=(255, 0, 0, 255)  # Red color
            )
                print(f"Red dot drawn at adjusted position ({object_x}, {object_y})")

        # Save the modified image back to the same file path
            image.save(file_path)
            

        except Exception as e:
              print(f"Failed to process image: {e}")
        return jsonify({"error": "Image processing failed"}), 500



    if file_type == "RGB":
        object_position = (object_x,object_y)
        ProccedFile = os.path.join(UPLOAD_FOLDER,urlid+"_rm.png")
        #call_Fast3D(file_path, "./output", urlid)
        call_removebg_subprocess( file_path, ProccedFile, object_position,urlid)
    if file_type == "Mask":
        object_position = (object_x,object_y)
        rgb = os.path.join(UPLOAD_FOLDER, urlid+".png")
        print(prompt)
        call_SDimg("http://127.0.0.1:7860", f'{urlid}_Modify.png', "img2img", prompt, input_image=rgb, mask_image=file_path)


    # Return the response including all received parameters for reference
    return jsonify({
        "message": "File uploaded and processed successfully",
        "file_path": file_path,
        "prompt": prompt,
        "type": file_type,  # Include the type field in the response
        "flipY": flip_y,
        "xOffset": x_offset,
        "objectPosition": (object_x, object_y),  # Return the modified coordinates
        "debugDraw": debug_draw
    }), 200


def capture_ndi_window_with_contrast_and_brightness(output_path="capture.png", alpha=2.0, beta=-50):
    """
    Capture the current NDI frame, enhance contrast, and lower brightness.
    
    Parameters:
        output_path (str): Path to save the image.
        alpha (float): Contrast adjustment factor (1.0 = no change, >1.0 increases contrast).
        beta (int): Brightness adjustment value (negative to lower brightness, positive to increase).
    """
    global ndi_frame

    if ndi_frame is not None:
        try:
            # Adjust contrast and brightness
            adjusted_frame = cv2.convertScaleAbs(ndi_frame, alpha=alpha, beta=beta)

            # Save the adjusted frame as a PNG image
            cv2.imwrite(output_path, adjusted_frame)
            print(f"NDI window with enhanced contrast and lowered brightness saved to {output_path}")
        except Exception as e:
            print(f"Error capturing NDI window: {e}")
    else:
        print("No NDI frame available to capture.")


def capture_ndi_window_with_contour_enhancement(output_path="capture_contour.png"):
    """
    Capture the current NDI frame, enhance contours, and save the result.
    
    Parameters:
        output_path (str): Path to save the enhanced image.
    """
    global ndi_frame

    if ndi_frame is not None:
        try:
            # Convert to grayscale for edge detection
            gray_frame = cv2.cvtColor(ndi_frame, cv2.COLOR_BGR2GRAY)

            # Apply Canny edge detection
            edges = cv2.Canny(gray_frame, threshold1=50, threshold2=150)

            # Convert edges to a 3-channel image
            edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

            # Blend the edges with the original frame to enhance contours
            enhanced_frame = cv2.addWeighted(ndi_frame, 0.8, edges_colored, 0.5, 0)

            # Save the enhanced frame as a PNG image
            cv2.imwrite(output_path, enhanced_frame)
            print(f"NDI window with enhanced contours saved to {output_path}")
        except Exception as e:
            print(f"Error capturing NDI window: {e}")
    else:
        print("No NDI frame available to capture.")




import subprocess




def adjust_contrast(frame, alpha=1.5, beta=0):
    """
    Adjusts contrast and brightness of the image.
    Alpha: Contrast control [1.0-3.0]
    Beta: Brightness control [0-100]
    """
    return cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)


def capture_ndi_window_with_adjusted_contrast(output_path="capture.png"):
    global ndi_frame

    if ndi_frame is not None:
        try:
            enhanced_frame = adjust_contrast(ndi_frame, alpha=2.0, beta=30)
            cv2.imwrite(output_path, enhanced_frame)
            print(f"NDI window with adjusted contrast saved to {output_path}")
        except Exception as e:
            print(f"Error capturing NDI window: {e}")
    else:
        print("No NDI frame available to capture.")



def capture_ndi_window(output_path="capture.png"):
    global ndi_frame

    if ndi_frame is not None:
        try:
            # Save the current NDI frame as a PNG image
            cv2.imwrite(output_path, ndi_frame)
            print(f"NDI window captured and saved to {output_path}")
        except Exception as e:
            print(f"Error capturing NDI window: {e}")
    else:
        print("No NDI frame available to capture.")



def call_Fast3D(input_file, output_dir, zipfile_name):
    # Command and arguments
    command = "python"
    script = "Fast3D.py"

    # Construct the command as a list with proper flags
    cmd = [
        command,
        script,
        "--input_file", input_file,
        "--output_dir", output_dir,
        "--urlid", zipfile_name
    ]

    try:
        # Run the command
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Subprocess executed successfully!")
        print("Output:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error while executing the subprocess.")
        print(f"Return Code: {e.returncode}")
        print(f"Output: {e.output}")
        print(f"Error: {e.stderr}")

        
        
        
def call_SDimg(server_url, output_file_name, mode, prompt, input_image=None, mask_image=None, 
                          seed=1, steps=20, width=512, height=512, cfg_scale=7.0, denoising_strength=0.5):
    """
    Calls the SDimg.py script as a subprocess with the specified arguments.

    Arguments:
    - server_url: URL of the server (e.g., http://127.0.0.1:7862).
    - output_file_name: Base name for the output files.
    - mode: 'txt2img' or 'img2img' to select the API.
    - prompt: Text prompt for the API.
    - input_image: Path to the input image (required for img2img mode).
    - mask_image: Path to the mask image (optional for img2img mode).
    - seed: Seed for the image generation.
    - steps: Number of steps for generation.
    - width: Width of the generated image.
    - height: Height of the generated image.
    - cfg_scale: CFG scale for image generation.
    - denoising_strength: Denoising strength (for img2img mode).
    """
    try:
        # Construct the command
        command = [
            "python", "SDimg.py", 
            "--server_url", server_url,
            "--output_file_name", output_file_name,
            "--mode", mode,
            "--prompt", prompt,
            "--seed", str(seed),
            "--steps", str(steps),
            "--width", str(width),
            "--height", str(height),
            "--cfg_scale", str(cfg_scale)
        ]

        if mode == "img2img":
            if not input_image:
                raise ValueError("input_image is required for img2img mode.")
            command.extend(["--input_image", input_image])
            if mask_image:
                command.extend(["--mask_image", mask_image])
            command.extend(["--denoising_strength", str(denoising_strength)])
        
        # Call the script as a subprocess
        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        # Handle subprocess results
        if result.returncode == 0:
            print("Subprocess completed successfully!")
            print(result.stdout)
            
            
            
            
        else:
            print("Subprocess failed!")
            print(result.stderr)

    except Exception as e:
        print(f"Error calling subprocess: {e}")
        
        
        
        
        
        

def call_removebg_subprocess( input_file, output_file, point_data,urlid):
    """
    Calls the removebg script as a subprocess.

    Parameters:
        script_path (str): Path to the `removebg_sam.py` script.
        input_file (str): Path to the input image file.
        output_file (str): Path to save the output image.
        point_data (list): List of two integers representing the point data (e.g., [150, 300]).
        checkpoint_path (str): Path to the SAM model checkpoint.
    """
    try:
        # Convert point_data list to a comma-separated string
        point_data_str = ",".join(map(str, point_data))

        # Call the script as a subprocess
        result = subprocess.run(
            [
                "python", f'removebg_sam.py',
                "--input_file", input_file,
                "--output_file", output_file,
                "--point_data", point_data_str,
                "--checkpoint_path","sam_vit_h_4b8939.pth"
            ],
            capture_output=True,
            text=True
        )

        # Handle subprocess results
        if result.returncode == 0:
            print("Subprocess completed successfully!")
            #call_Fast3D(output_file,"./output",urlid)
            print(result.stdout)
        else:
            print("Subprocess failed!")
            print(result.stderr)

    except Exception as e:
        print(f"Error calling subprocess: {e}")



def ndi_receiver():
    global ndi_frame

    if not ndi.initialize():
        print("Cannot initialize NDI")
        return 0

    ndi_find = ndi.find_create_v2()

    if ndi_find is None:
        print("Cannot create NDI find")
        return 0

    sources = []
    while not len(sources) > 0:
        print('Looking for NDI sources...')
        ndi.find_wait_for_sources(ndi_find, 1000)
        sources = ndi.find_get_current_sources(ndi_find)

    print("NDI sources found:", sources)
    ndi_recv_create = ndi.RecvCreateV3()
    ndi_recv_create.color_format = ndi.RECV_COLOR_FORMAT_BGRX_BGRA

    ndi_recv = ndi.recv_create_v3(ndi_recv_create)

    if ndi_recv is None:
        print("Cannot create NDI receiver")
        return 0

    ndi.recv_connect(ndi_recv, sources[0])

    ndi.find_destroy(ndi_find)

    while True:
        t, v, _, _ = ndi.recv_capture_v2(ndi_recv, 5000)

        if t == ndi.FRAME_TYPE_VIDEO:
            frame = np.copy(v.data)
            ndi.recv_free_video_v2(ndi_recv, v)
            # Convert 4-channel BGRX_BGRA to 3-channel BGR
            ndi_frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        if cv2.waitKey(1) & 0xff == 27:
            break

    ndi.recv_destroy(ndi_recv)
    ndi.destroy()


def ipcam_receiver(url):
    global ipcam_frame

    while True:
        try:
            cap = requests.get(url, stream=True, timeout=10)
            if cap.status_code == 200:
                bytes = b''
                for chunk in cap.iter_content(chunk_size=1024):
                    bytes += chunk
                    a = bytes.find(b'\xff\xd8')
                    b = bytes.find(b'\xff\xd9')
                    if a != -1 and b != -1:
                        jpg = bytes[a:b+2]
                        bytes = bytes[b+2:]
                        ipcam_frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        
            #             if(isTracking):
            #                 results = objectron.process(ipcam_frame)
            #                 if results.detected_objects:
            #                  for detected_object in results.detected_objects:
            # #print(detected_object)
            #                     mp_drawing.draw_landmarks(ipcam_frame, 
            #                           detected_object.landmarks_2d, 
            #                           mp_objectron.BOX_CONNECTIONS)
          
            #                     mp_drawing.draw_axis(ipcam_frame, 
            #                         detected_object.rotation,
            #                         detected_object.translation)
            else:
                print("Failed to connect to the server, status code:", cap.status_code)
                time.sleep(5)  # Wait before trying to reconnect
        except requests.exceptions.RequestException as e:
            print("Connection error:", e)
            time.sleep(5)  # Wait before trying to reconnect
        except Exception as e:
            print("An unexpected error occurred:", e)
            time.sleep(5)  # Wait before trying to reconnect




def NDIShow():
    global ndi_frame

    # Start the NDI receiver thread

    while True:
        if ndi_frame is not None:
            cv2.imshow('NDI Stream', ndi_frame)

        if cv2.waitKey(1) & 0xff == 27:
            break

    cv2.destroyAllWindows()



def flask_server():
    app.run(host='0.0.0.0', port=5000)


def run_server_process():
    subprocess.run(["RunServer.bat", "8000"], shell=True)




if __name__ == '__main__':
    # call_SDimg("http://127.0.0.1:7860", 'SD_test.png', "img2img", "ice cream", input_image="./uploads/Cup.png", mask_image="./uploads/Mask.png")
    # ipcam_url=""
    # ipcam_thread = threading.Thread(target=ipcam_receiver, args=(ipcam_url,))
    # ipcam_thread.daemon = True
    # ipcam_thread.start()

    # ndi_thread = threading.Thread(target=ndi_receiver)
    # ndi_thread.daemon = True
    # ndi_thread.start()

    # # Thread for displaying NDI stream
    # display_thread = threading.Thread(target=NDIShow)
    # display_thread.daemon = True
    # display_thread.start()


    # Thread for Flask app
    flask_thread = threading.Thread(target=flask_server)
    flask_thread.daemon = True
    flask_thread.start()

    # Thread for running the external server process
    server_thread = threading.Thread(target=run_server_process)
    server_thread.daemon = True
    server_thread.start()



    while True:
        pass




