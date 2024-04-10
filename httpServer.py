from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import cgi
import subprocess
import os
import json
import time
Inpainting_Anything_ModulePath ="C:\\Users\\someo\\Desktop\\RealityEditor\\PythonProject\\Inpaint-Anything\\"

class BasicRequestHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
class  EnhancedRequestHandler(BaseHTTPRequestHandler):
   
    def do_POST(self):
        
        if self.path == '/upload':
            form = cgi.FieldStorage(
                fp=self.rfile, 
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']}
            )
            uploaded_file = form['file']
            coordinates = (form.getvalue('xCoordinate'), form.getvalue('yCoordinate'))
            URLID = form.getvalue('URLID'); 
            
            print(f"Received coordinates: ({coordinates})")

            with open(f'{URLID}.jpg', 'wb') as f:
                f.write(uploaded_file.file.read())
                
            # print(uploaded_file)
            
            imagePth=os.path.abspath(f'{URLID}.jpg')

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'File and coordinates uploaded successfully')
            path=os.path.abspath(os.getcwd())
            
            self.run_inpainting(imagePth,path,URLID,coordinates)
            
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404 Not Found')
            
    def do_GET(self):
        # Assuming the GET request is to download a file
        try:
            # Extract the file name from the request path
            file_name = self.path.strip("/")  # Remove leading slash
            # Ensure the file path is safe to use
            if not os.path.isfile(file_name):
                raise FileNotFoundError
            
            # Set headers
            self.send_response(200)
            self.send_header('Content-type', 'application/octet-stream')  # Adjust content-type if necessary
            self.send_header('Content-Disposition', f'attachment; filename="{os.path.basename(file_name)}"')
            self.end_headers()

            # Serve the file
            with open(file_name, 'rb') as file:
                self.wfile.write(file.read())
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'File not found')
   
    def run_inpainting(self,input_img, output_dir,URLid,coordinates):
        
        coordinates_int = [int(round(float(coord))) for coord in coordinates]
        coordinates_int[1] += 150
        coordinates_str = ' '.join(map(str, coordinates_int))
       
        global Inpainting_Anything_ModulePathW
    # Execute the command
        result = subprocess.run(f"python {Inpainting_Anything_ModulePath}/RemoveSingleObject.py --input_img {input_img} --coords_type \"key_in\" --point_coords {coordinates_str} --point_labels 1 --dilate_kernel_size 15 --output_dir {output_dir} --sam_model_type \"vit_h\" --sam_ckpt {Inpainting_Anything_ModulePath}\\pretrained_models\\sam_vit_h_4b8939.pth --lama_config {Inpainting_Anything_ModulePath}\\lama\\configs\\prediction\\default.yaml --lama_ckpt  {Inpainting_Anything_ModulePath}\\pretrained_models\\big-lama --URID {URLid} ")

    # Check if the command was executed successfully
        if result.returncode == 0:
            print("Command executed successfully.")
        
def run_additional_server(server_class=HTTPServer, handler_class=BasicRequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting additional server on port {port}...')
    httpd.serve_forever()
       
           

def main_server(server_class=HTTPServer, handler_class=EnhancedRequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting server on port {port}...')
    httpd.serve_forever()

def load_config(config_file):
    with open(config_file, 'r') as file:
        config = json.load(file)
    return config

if __name__ == '__main__':

    config_path = './config.json'  # Update this path to where you save your config.json
    config = load_config(config_path)
    Inpainting_Anything_ModulePath = config['Inpainting_Anything_ModulePath']
        # Start the main server in a separate thread
    main_server_thread = threading.Thread(target=main_server)
    main_server_thread.start()

    # Start the additional server in a separate thread
    # additional_server_thread = threading.Thread(target=run_additional_server)
    # additional_server_thread.start()
    
    
