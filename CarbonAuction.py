from flask import Flask, request, jsonify
import json
from RealityEditorManager import GeneratedModel
import time
from pythonosc import dispatcher, osc_server, udp_client
import threading
import subprocess

app = Flask(__name__)

RoomJson = None
roomprocessing = False


# Flask Routes
@app.route('/receiveCropBox', methods=['POST'])
def receive_crop_box():
    data = request.get_json()
    print(f"Received CropBox data: {data}")
    return jsonify({"message": "CropBox JSON received successfully"}), 200

@app.route('/AuctionSimulation', methods=['POST'])
def receive_AuctionSimStart():
    try:
        # Parse the incoming JSON request
        data = request.get_json()

        # Extract the filename and URLs from the JSON data
        filename = data.get("filename")
        url_list = data.get("data", {}).get("urls", [])
        
        url_count = len(url_list)
        
        
        call_Interactable_script(f"Give me {url_count} objects with their ids {url_list}", filename, "instruction")

        if not filename or not url_list:
            return jsonify({"error": "Invalid JSON format"}), 400

        # Debug information (optional)
        print(f"Received filename: {filename}")
        print(f"Received URLs: {url_list}")

        # Example: Save the data to a file
        with open(f"{filename}.txt", "w") as file:
            file.write("\n".join(url_list))

        # Return a success response
        return jsonify({"status": "success", "message": "Data received and processed"}), 200

    except Exception as e:
        # Handle errors
        print(f"Error processing request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/receiveRoom', methods=['POST'])
def receive_room():
    global RoomJson
    global roomprocessing
    

    # Get the incoming JSON data
    data = request.get_json()

    # Extract the filename from the data
    filename = data.get("filename", "default_filename.json")  # Use a default value if no filename is provided

    # Save the rest of the data to RoomJson
    RoomJson = data.get("data", {})
    print(f"Received filename: {filename}")

    roomprocessing = True

    # Call the script and pass the RoomJson and filename
    call_Interactable_script(RoomJson, filename, 'FireRoom')

    return jsonify({"message": "Room JSON received successfully"}), 200





@app.route('/receiveMesh', methods=['POST'])
def receive_mesh():
    data = request.get_json()
    print(f"Received Mesh data: {data}")
    return jsonify({"message": "Mesh JSON received successfully"}), 200

# OSC Handler


def call_Interactable_script(prompt, output_path, instruction):
    global open_ai_key
    # Construct the command to call the external script
    prompt_str = json.dumps(prompt)

    command = [
        'python', 'send_openai_prompt.py',
        '--prompt', prompt_str,
        '--api_key', open_ai_key,
        '--output_path', output_path,
        '--instructions_file', f'./PromptInstructions/{instruction}.txt'
    ]
    
    # Run the command using subprocess.Popen
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Communicate with the process to capture stdout and stderr
    stdout, stderr = process.communicate()
    
    # Print the output and errors (if any)
    if process.returncode == 0:
        print("Command executed successfully!")
        print("STDOUT:", stdout)
    else:
        print("Command failed!")
        print("STDERR:", stderr)


# Function to start Flask server
def start_flask_server():
    app.run(host='0.0.0.0', port=5000)

def load_config(config_file):
    with open(config_file, 'r') as file:
        config = json.load(file)
    return config

open_ai_key=""
# Run both servers in parallel
if __name__ == '__main__':

    config = load_config('./config.json')
    # Inpainting_Anything_ModulePath = config['Inpainting_Anything_ModulePath']
    # InstantNGP_MoudlePath = config['InstantNGP_MoudlePath']
    # TexTurePaper_modulePath= config['TEXTurePaper_ModulePath']
    open_ai_key = config['open_ai_key']
    process = subprocess.Popen(["RunServer.bat","12000"], shell=True)

    # Start Flask server
    start_flask_server()
