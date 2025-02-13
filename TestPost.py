import requests

# Define the URL of your Flask server
url = "http://localhost:5000/command"  # Change this to match your server's address

def send_test_request(command, urlid, prompt):
    data = {
        "Command": command,
        "URLID": urlid,
        "Prompt": prompt
    }
    try:
        response = requests.post(url, data=data)
        print("Response Status Code:", response.status_code)
        print("Response JSON:", response.json())
    except Exception as e:
        print("Error sending request:", e )

# Test different commands
# send_test_request("IpcamCapture", "test1", "")
#send_test_request("ShapeE", "12345678", "a_cat")
send_test_request("DynamicCoding", "123456798", "A bear should continuously fly around in random directions in 3D space.")
