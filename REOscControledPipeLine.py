from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher
import asyncio
import subprocess
import zipfile
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import signal
import psutil
from pythonosc import osc_server
import keyboard
import sys



FileUploadCmd = r"python C:\Users\someo\Desktop\RealityEditor\PythonProject\gcpstorege\sftpupload.py"
GenerateModelwithPromptCMD = r'python C:\Users\someo\Desktop\RealityEditor\PythonProject/threestudio\launch.py --config C:\Users\someo\Desktop\RealityEditor\PythonProject\threestudio\configs\dreamfusion-sd.yaml --train --gpu 0 system.prompt_processor.prompt='

currentpid = -1
procesingisRunning = False
isInturupt=True
runingMethod = 0
argsarray = []









class PNGHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        # Check if the created file is a PNG file
        if event.src_path.lower().endswith(".png"):
            # Replace this line with your desired action
            print(f"New PNG file created: {event.src_path}")

def handler(s, f):
    
    pass

def zip_folder(folder_path, zip_path):
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname=arcname)

        print(f'Folder "{folder_path}" successfully zipped to "{zip_path}"')
    except Exception as e:
        print(f'Error zipping folder: {e}')

def activate_anaconda_environment(environment_name):
    try:
        # Construct the command to activate the Anaconda environment
        command = f"conda activate {environment_name}"

        # Use subprocess to run the command in the shell
        subprocess.run(command, shell=True, check=True)

        print(f"Activated Anaconda environment: {environment_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error activating Anaconda environment: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def filter_handler(address, *args):
    global procesingisRunning
    global runingMethod
    global argsarray
    global process
    global isInturupt

    if address == '/PromtGenerateModel':
        print(f"{address}: {args}")
        procesingisRunning = True
        runingMethod = 0
        argsarray = args
        StartGenerateModel(args[0], args[1])
    elif address == '/InstructNerfGenerateModel':
        print("You selected option 2")
    elif address == '/ScanModel':
        print("Scanning Model")
    elif address == '/stopProcess':
        
        send_keyboard_interrupt()
       
        procesingisRunning = False

    print(f"{address}: {args}")

def uploadFile(filePath):
    print({filePath})

def send_keyboard_interrupt():
    global process
    global isInturupt
    global currentpid
    #kill(process.pid)
    os.kill(process.pid,signal.CTRL_C_EVENT)
    #process.terminate()
    if(isInturupt==True):
        isInturupt=False
        
        #process.kill()
        
        #process.terminate()
        
    
       #process.wait()
       
       
def kill(proc_pid):
    process = psutil.Process(proc_pid)
    #process.terminate()
    print(process)
    print(len(process.children(recursive=True)))
    process.children(recursive=True)[0].send_signal(signal.CTRL_C_EVENT)
    
    # for proc in process.children(recursive=True):
    #     print(proc)
    
    #process.kill()       
        
    
    
        
        

def StartGenerateModel(id, prompt):
    global process
    global currentpid
    try:
        # Use subprocess to run the command in the shell
        #subprocess.run('conda activate NeRFStudio', shell=True, check=True)
        command = f"{GenerateModelwithPromptCMD}\"{prompt}\""
        process = subprocess.Popen( command, shell=True, cwd='C:\\Users\\someo\\Desktop\\RealityEditor\PythonProject\\threestudio')
        currentpid=process.pid
        print(os.getpid(), process.pid)
    except subprocess.CalledProcessError as e:
        print(f"Error starting GenerateModel process: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")



def main():
    global procesingisRunning
    global runingMethod
    global argsarray
    global isInturupt
    
    server = osc_server.ThreadingOSCUDPServer(
      ('127.0.0.1',12000), dispatcher)
    print("Serving on {}".format(server.server_address))
    print("Reality Editor pipeline server is On/Press Esc to exit")
    server.serve_forever()
   
   
    while True:
        pass    
       
        
    #     # if procesingisRunning:
           
    #     #     if runingMethod == 0:
    #     #         procesingisRunning=False
    #     #         subprocess_thread = threading.Thread(target=StartGenerateModel, args=(argsarray[0], argsarray[1]))
    #     #         subprocess_thread.start()
                
def ignore_interrupt(signal, frame):
    pass

# Register the custom signal handler for Ctrl+C (SIGINT)

          
def exit_program():
    print("Exiting the program.")
    os.kill(os.getpid(), signal.SIGTERM)     


if __name__ == "__main__":
    
    dispatcher = Dispatcher()
    dispatcher.map("/PromtGenerateModel", filter_handler)
    dispatcher.map("/InstructNerfGenerateModel", filter_handler)
    dispatcher.map("/ScanModel", filter_handler)
    dispatcher.map("/stopProcess", filter_handler)
    ip = "127.0.0.1"
    port = 12000
    keyboard.add_hotkey('esc', exit_program)

    
    signal.signal(signal.SIGINT, ignore_interrupt)
    try:
        main()
        
    except KeyboardInterrupt:
        print('no exit')
    






# async def init_main():
#     server = AsyncIOOSCUDPServer((ip, port), dispatcher, asyncio.get_event_loop())
#     transport, protocol = await server.create_serve_endpoint()  # Create datagram endpoint and start serving

#     await loop()  # Enter the main loop of the program

#     transport.close()  # Clean up serve endpoint

# asyncio.run(init_main())
