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

    def do_GET(self):
        print("DO_GET?!?!?!?!")
        # Check the requested path to determine the action
        if self.path == '/list-files':
            self.list_files()
        elif self.path.startswith('/download?filename='):
            self.send_file()
        else:
            # Send a 404 response if the path is not recognized
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found.')

    def list_files(self):
        print("in the function to send all the scene names back")

        # Directory where saved scene files are located
        save_directory = "SavedScene"
        try:
            # Check if the directory exists
            if not os.path.exists(save_directory):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'[]')  # Return an empty list if the folder does not exist
                return

            # Get all filenames in the directory
            file_names = [f for f in os.listdir(save_directory) if f.endswith('.json')]
            # Send the response with the filenames as a JSON array
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(file_names).encode('utf-8'))
        except Exception as e:
            print("Error retrieving filenames:", e)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Error retrieving filenames.')

    def send_file(self):
        print("in the function to send a scene back")
        # Extract the filename from the request path
        filename = self.path.split('=')[-1]
        save_directory = "SavedScene"
        file_path = os.path.join(save_directory, filename)

        # Check if the file exists
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                # Send the file content back to the client
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(file_content.encode('utf-8'))
            except Exception as e:
                print(f"Error reading file {filename}: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'Error reading the file.')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'File not found.')

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting Python HTTP server on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()
