from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc.udp_client import SimpleUDPClient
from pythonosc import osc_server
import asyncio
import tornado.ioloop
import tornado.web
import tornado.websocket



import subprocess
import zipfile
import os
import time

import threading
import signal
import psutil

import keyboard
import sys


class WebSocketClient(tornado.websocket.WebSocketClientConnection):
    async def on_message(self, message):

        
        
        
        print(f"收到消息: {message}")
        
async def WSmain():
    # WebSocket 服務器地址
    server_url = "ws://34.106.250.143:8888/websocket"

    try:
        # 連線到 WebSocket 服務器
        client = await tornado.websocket.websocket_connect(server_url)
        print("已連線到 WebSocket Server")

        while True:
            message = await client.read_message()  # 監聽来自服務器的訊息
            if message is None:
                print("連線已關閉")
                break
            WsMessageProcessing(message)
            print("收到消息:", message)

    except Exception as e:
        print(f"error: {e}")
        


def WsMessageProcessing(message):
    datas=message.split(',')
    address=datas[0]
    objid=datas[1]
    prompt=datas[2]
    
    
    
    global procesingisRunning
    global runingMethod
    global argsarray
    global process
    global isInturupt

    if address == '/PromtGenerateModel':
        #print(f"{address}: {args}")
        procesingisRunning = True
        runingMethod = 0
        argsarray = prompt
        #StartGenerateModel(objid,prompt)
    elif address == '/InstructNerfGenerateModel':
        print("You selected option 2")
    elif address == '/ScanModel':
        print("Scanning Model")
    elif address == '/stopProcess':
        send_keyboard_interrupt()
        procesingisRunning = False

    #print(f"{address}: {args}")

    





VRip=r'127.0.0.1'

threeStudioPath=r'D:\Desktop\RealityEditor\PythonProject\threestudio'

GenerateModelwithPromptCMD = f'python {threeStudioPath}\launch.py --config {threeStudioPath}\configs\dreamfusion-sd.yaml --train --gpu 0 system.prompt_processor.prompt='

currentpid = -1
procesingisRunning = False
isInturupt=True
runingMethod = 0
argsarray = []





def send_osc_message(ip, port, address, data):
    try:
        client = SimpleUDPClient(ip, port)  # Create client
        client.send_message(address, data)  # Send OSC message
    except Exception as e:
        print(f"Error sending OSC message: {e}")

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
        StartGenerateModel(args[0], args[1],args[2])
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
        
    
    
        
        

def StartGenerateModel(id, prompt,urlid):
    global process
    global currentpid
    send_osc_message('127.0.0.1', 6161, "updateID", urlid)
    try:
        # Use subprocess to run the command in the shell
        #subprocess.run('conda activate NeRFStudio', shell=True, check=True)
        command = f"{GenerateModelwithPromptCMD}\"{prompt}\""
        process = subprocess.Popen( command, shell=True, cwd=threeStudioPath)
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
      ('192.168.0.139',8888), dispatcher)
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
    ip = VRip
    port = 8888
    keyboard.add_hotkey('esc', exit_program)

 #   asyncio.get_event_loop().run_until_complete(WSmain())
    tornado.ioloop.IOLoop.current().start()


    
    signal.signal(signal.SIGINT, ignore_interrupt)
    try:
        main()
        
    except KeyboardInterrupt:
        print('no exit')
    