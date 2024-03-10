import requests
import base64
import os
import sys
import argparse

class SHAPERuntime:
    def __init__(self):
        self.prompt = ""
        self.steps = 64
        self.cfg = 20
        self.directory_path = "./output" #do not use / at the end (check line 70)
        self.model_name = ""
        self.format = "obj"
        self.post_flag = False
        self.post_progress = 0
        self.text_to_mesh_id = "nejnwmcwvhcax9"
        self.invoice = "20067068964066"
        self.model_id = ""
        self.user_id = ""
        self.model_downloader = None

    def start(self):
        self.verify(f"https://{self.text_to_mesh_id}-5000.proxy.runpod.net/verify", f'{{"invoice":"{self.invoice}"}}')
        # self.post(f"https://{self.text_to_mesh_id}-5000.proxy.runpod.net/data", f'{{"prompt":"{self.prompt}","steps":"{self.steps}","cfg":"{self.cfg}","invoice":"{self.invoice}","fileFormat":"{self.format}"}}')

    def send_prompt(self, user_id, prompts, model_id):
        self.model_id = model_id
        self.user_id = user_id
        if self.model_downloader is None:
            self.post(f"https://{self.text_to_mesh_id}-5000.proxy.runpod.net/data", f'{{"prompt":"{prompts}","steps":"{self.steps}","cfg":"{self.cfg}","invoice":"{self.invoice}","fileFormat":"{self.format}"}}')
        else:
            self.post_to_trilib(f"https://{self.text_to_mesh_id}-5000.proxy.runpod.net/data", f'{{"prompt":"{prompts}","steps":"{self.steps}","cfg":"{self.cfg}","invoice":"{self.invoice}","fileFormat":"{self.format}"}}')

    def debug_sending(self):
        self.prompt = input("Enter prompt: ")
        # self.send_prompt("12", self.prompt, "XXX")
        self.post(f"https://{self.text_to_mesh_id}-5000.proxy.runpod.net/data", f'{{"prompt":"{self.prompt}","steps":"{self.steps}","cfg":"{self.cfg}","invoice":"{self.invoice}","fileFormat":"{self.format}"}}')
        print("Sent")

    def update(self):
        pass

    def post_to_trilib(self, url, body_json_string):
        headers = {"Content-Type": "application/json"}
        body_raw = body_json_string.encode('utf-8')
        response = requests.post(url, data=body_raw, headers=headers)

        if self.model_downloader is not None:
            self.model_downloader.load_model_web_request(response)

    def post(self, url, body_json_string):
        headers = {"Content-Type": "application/json"}
        body_raw = body_json_string.encode('utf-8')
        response = requests.post(url, data=body_raw, headers=headers)

        self.post_progress = 1
        self.post_flag = False

        if response.status_code != 200:
            print(f"There was an error in generating the model. \nPlease check your invoice/order number and try again or check the troubleshooting section in the documentation for more information."
                  f"\nInfo: {response.status_code}\nError Code: {response.text}")
        else:
            if response.text == "Invalid Response":
                print("Invalid Invoice/Order Number. Please check your invoice/order number and try again")
            elif response.text == "Limit Reached":
                print("It seems that you may have reached the limit. To check your character usage, please click on the Status button. Please wait until the 1st of the next month to get a renewed character count. Thank you for using Shap-E for Unity.")
            else:
                self.model_name = self.model_id+"_generated"
                model_data = base64.b64decode(response.text)
                dpath = f"{self.directory_path}/{self.model_id}"
                if not os.path.exists(dpath):
                    os.makedirs(dpath)  # create directory if it doesn't exist 
                                             
                with open(f"{dpath}/{self.model_name}.{self.format}", "wb") as model_file:
                    model_file.write(model_data)
                print(f"Inference Successful: Please find the model in the {self.directory_path}")
                self.broadcast_message("Done")

    def verify(self, url, body_json_string):
        headers = {"Content-Type": "application/json"}
        body_raw = body_json_string.encode('utf-8')
        response = requests.post(url, data=body_raw, headers=headers)

        if response.status_code != 200:
            print(response.text)
        else:
            if response.text == "Not Verified":
                print("Invoice/Order number verification unsuccessful. Please check your invoice/order number and try again or contact the publisher on the email given in the documentation.")
            else:
                print(f"Your invoice is verified. You have generated {response.text} objects. Thank you for choosing Shap-E for Unity!")

    def broadcast_message(self, message):
        pass  # Implement your broadcasting logic here


def parse_args():
    parser = argparse.ArgumentParser(description="Generate and process a YAML file based on command line arguments.")
    parser.add_argument("--URID", required=True, help="Unique Resource Identifier")
    parser.add_argument("--prompt", required=True, help="Text prompt for guide")
    return parser.parse_args()


if __name__ == '__main__':
    
# Example Usage
    args = parse_args()

    
    prompt = args.prompt
    model_id = args.URID
    shaperuntime_instance = SHAPERuntime()
    shaperuntime_instance.start()
    print("Start Generating \"prompt\" ")   
    shaperuntime_instance.send_prompt('', prompt, model_id)
 

