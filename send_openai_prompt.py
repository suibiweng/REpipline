import requests
import argparse
import json

def generate_payload(api_key, prompt):
    """Generates the payload for sending a request to the OpenAI API."""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4",  # Make sure you are using the right model name.
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 300
    }

    return headers, payload

def main():
    parser = argparse.ArgumentParser(description="Send prompt to OpenAI API, create assistant, and save the response as a JSON file")
    
    parser.add_argument('--prompt', type=str, required=True, help="Prompt for the API")
    parser.add_argument('--api_key', type=str, required=True, help="OpenAI API Key")
    parser.add_argument('--output_path', type=str, required=True, help="Path to save the output JSON file")
    parser.add_argument('--instructions_file', type=str, required=True, help="Path to the instructions text file")
    
    args = parser.parse_args()

    # Read instructions from the text file (you can include the instructions as part of the prompt)
    with open(args.instructions_file, 'r') as file:
        instructions = file.read()

    # Combine prompt and instructions if needed
    combined_prompt = f"{instructions}\n{args.prompt}"

    # Generate the payload without description and instructions
    headers, payload = generate_payload(args.api_key, combined_prompt)

    # Send request to OpenAI API
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    # Extract only the content of the assistant's message
    response_json = response.json()
    assistant_content = response_json['choices'][0]['message']['content']

    # Parse the content as JSON if it's in that format
    try:
        assistant_content_json = json.loads(assistant_content)
    except json.JSONDecodeError:
        assistant_content_json = {"content": assistant_content}

    # Save the extracted content as a JSON file
    with open(args.output_path, 'w') as json_file:
        json.dump(assistant_content_json, json_file, indent=4)

    print(f"Extracted response saved to {args.output_path}")

if __name__ == "__main__":
    main()
