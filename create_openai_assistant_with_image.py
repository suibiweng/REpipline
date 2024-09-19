import base64
import requests
import argparse
import json

def encode_image(image_path):
    """Encodes an image to base64 format."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def generate_payload(api_key, image_path, prompt, description, instructions):
    """Generates the payload for sending a request to the OpenAI API."""
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
                        "text": prompt
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
        "description": description,
        "instructions": instructions,
        "max_tokens": 300
    }

    return headers, payload

def main():
    parser = argparse.ArgumentParser(description="Send image and prompt to OpenAI API, create assistant, and save the response as a JSON file")
    
    parser.add_argument('--image_path', type=str, required=True, help="Path to the image file")
    parser.add_argument('--prompt', type=str, required=True, help="Prompt for the API")
    parser.add_argument('--api_key', type=str, required=True, help="OpenAI API Key")
    parser.add_argument('--output_path', type=str, required=True, help="Path to save the output JSON file")
    parser.add_argument('--description', type=str, required=True, help="Description for the assistant")
    parser.add_argument('--instructions', type=str, required=True, help="Instructions for the assistant")
    
    args = parser.parse_args()

    # Generate the payload with description and instructions
    headers, payload = generate_payload(args.api_key, args.image_path, args.prompt, args.description, args.instructions)

    # Send request to OpenAI API
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    # Save the response as a JSON file
    with open(args.output_path, 'w') as json_file:
        json.dump(response.json(), json_file, indent=4)

    print(f"Response saved to {args.output_path}")

if __name__ == "__main__":
    main()
