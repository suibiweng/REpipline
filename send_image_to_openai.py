import openai
import base64
import requests
import argparse
import json

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def generate_payload(api_key, image_path, prompt):
    # Getting the base64 string
    base64_image = encode_image(image_path)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{prompt}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 300
    }

    return headers, payload

def main():
    parser = argparse.ArgumentParser(description="Send image and prompt to OpenAI API and save the response as a JSON file")
    parser.add_argument('--image_path', type=str, required=True, help="Path to the image file")
    parser.add_argument('--prompt', type=str, required=True, help="Prompt for the API")
    parser.add_argument('--api_key', type=str, required=True, help="OpenAI API Key")
    parser.add_argument('--output_path', type=str, required=True, help="Path to save the output JSON file")
    
    args = parser.parse_args()
    
    headers, payload = generate_payload(args.api_key, args.image_path, args.prompt)
    
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    
    # Saving the response as a JSON file
    with open(args.output_path, 'w') as json_file:
        json.dump(response.json(), json_file, indent=4)
    
    print(f"Response saved to {args.output_path}")

if __name__ == "__main__":
    main()
