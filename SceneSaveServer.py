from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Read the content length from headers
        content_length = int(self.headers['Content-Length'])
        # Read the POST data
        post_data = self.rfile.read(content_length)
        # Decode the JSON data
        json_data = post_data.decode('utf-8')
        
        try:
            data = json.loads(json_data)
            # Extract the scene name, replace any characters that are invalid for file names
            scene_name = data.get("sceneName", "default_scene").replace(":", "_").replace(" ", "_")
            print(f"Received scene name: {scene_name}")
        except json.JSONDecodeError as e:
            print("Invalid JSON data received:", e)
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid JSON data.')
            return

        # Create the "SavedScene" folder if it doesn't exist
        save_directory = "SavedScene"
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)
        
        # Path to save the JSON file in the "SavedScene" folder
        save_path = os.path.join(save_directory, f'{scene_name}.json')
        
        # Optionally, you can parse the JSON data
        try:
            data = json.loads(json_data)
            print("Received JSON data:", data)
        except json.JSONDecodeError as e:
            print("Invalid JSON data received:", e)

        # Save the JSON data to the specified path
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(json_data)

        # Send an HTTP response
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'JSON file received and saved.')

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting Python HTTP server on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()
