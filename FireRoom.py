from flask import Flask, request, jsonify
import json
from RealityEditorManager import GeneratedModel, call_Interactable_script
import time
from pythonosc import dispatcher, osc_server, udp_client
import threading

app = Flask(__name__)

RoomJson = None
FireSequence = []
roomprocessing = False

# OSC Client to send messages
client = udp_client.SimpleUDPClient("localhost", 5005)

# Flask Routes
@app.route('/receiveCropBox', methods=['POST'])
def receive_crop_box():
    data = request.get_json()
    print(f"Received CropBox data: {data}")
    return jsonify({"message": "CropBox JSON received successfully"}), 200

@app.route('/receiveRoom', methods=['POST'])
def receive_room():
    global RoomJson
    global roomprocessing
    global FireSequence
    data = request.get_json()
    RoomJson = data
    print(f"Received Room data: {data}")
    roomprocessing = True

    # Call the script and wait for the fire sequence to be processed
    call_Interactable_script(RoomJson, "FireRoom.json", "Fireroom.txt")
    
    time.sleep(60)  # Sleep for 60 seconds to wait for processing

    # Load the FireSequence from the file (assuming it's JSON format)
    with open("FireRoom.json", 'r') as f:
        FireSequence = json.load(f)

    return jsonify({"message": "Room JSON received successfully"}), 200

@app.route('/receiveMesh', methods=['POST'])
def receive_mesh():
    data = request.get_json()
    print(f"Received Mesh data: {data}")
    return jsonify({"message": "Mesh JSON received successfully"}), 200

# OSC Handler
def osc_PutoutFire_handler(unused_addr, *args):
    global FireSequence

    # Extract URID from OSC message (assuming it's passed as the first argument)
    urid = args[0]
    print(f"Received OSC message to put out fire for URID: {urid}")

    # Find the furniture in FireSequence by URID
    current_index = None
    for i, item in enumerate(FireSequence):
        if item["URID"] == urid:
            current_index = i
            break

    if current_index is not None:
        # If the item is found and there is a next item, send the next one via OSC
        if current_index + 1 < len(FireSequence):
            next_item = FireSequence[current_index + 1]
            next_urid = next_item["URID"]
            print(f"Next item in fire sequence: {next_item}")
            
            # Send the next URID via OSC with the /setFire address
            client.send_message("/setFire", next_urid)
            print(f"Sent OSC message: /setFire {next_urid}")
        else:
            print("No more items left in the fire sequence.")
    else:
        print(f"URID {urid} not found in the FireSequence.")

# OSC Server Setup
def start_osc_server():
    disp = dispatcher.Dispatcher()

    # Mapping OSC addresses to handler functions
    disp.map("/PutOutFire", osc_PutoutFire_handler)

    # OSC server listening on port 5005
    server = osc_server.ThreadingOSCUDPServer(("localhost", 5005), disp)
    print("OSC Server is running on port 5005...")
    server.serve_forever()

# Function to start Flask server
def start_flask_server():
    app.run(host='localhost', port=5000)

# Run both servers in parallel
if __name__ == '__main__':
    # Start OSC server in a separate thread
    osc_thread = threading.Thread(target=start_osc_server)
    osc_thread.daemon = True  # Allows the thread to close when the main program exits
    osc_thread.start()

    # Start Flask server
    start_flask_server()
