import requests
import argparse
import json
import os
import re

def generate_payload(api_key, prompt):
    """Generates the payload for sending a request to the OpenAI API."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "gpt-4",  # Ensure the model name is correct
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1000
    }
    return headers, payload

def load_config(config_file):
    with open(config_file, 'r') as file:
        config = json.load(file)
    return config

def remove_markdown_backticks(text):
    """Removes ```json and ``` markers if present."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    if text.startswith("```"):
        text = text[len("```"):].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text

def smart_clean_json_response(bad_json_text):
    """Attempts a smarter fix for raw API responses with embedded Lua code issues."""
    inside_lua = False
    cleaned_lines = []

    for line in bad_json_text.splitlines():
        # Check if entering lua_code field
        if '"lua_code": "' in line:
            inside_lua = True
            cleaned_lines.append(line.strip())
            continue
        
        if inside_lua:
            # Check if this line ends the lua_code string
            if line.strip().endswith('",') or line.strip().endswith('"'):
                inside_lua = False
                cleaned_lines.append(line.strip())
                continue
            
            # Otherwise, clean this Lua line
            line = line.strip()
            line = line.replace('"', r'\"')  # Escape quotes inside Lua
            cleaned_lines.append(line)
        else:
            cleaned_lines.append(line.strip())

    # Merge cleaned lines into one string
    cleaned_json = ''.join(cleaned_lines)
    return cleaned_json

def main():
    config_path = './config.json'
    config = load_config(config_path)
    open_ai_key = config['open_ai_key']
    
    parser = argparse.ArgumentParser(description="Send prompt to OpenAI API, create assistant, and save the response as a JSON file")
    parser.add_argument('--prompt', type=str, required=True, help="Prompt for the API")
    parser.add_argument('--api_key', type=str, default=open_ai_key, help="OpenAI API Key (default: from config.json)")
    parser.add_argument('--output_path', type=str, required=True, help="Path to save the output JSON file")
    parser.add_argument('--instructions_file', type=str, required=True, help="Path to the instructions text file")

    args = parser.parse_args()

    # Check if instructions file exists
    if not os.path.exists(args.instructions_file):
        print(f"Error: Instructions file '{args.instructions_file}' not found.")
        return

    # Read instructions from the file
    with open(args.instructions_file, 'r') as file:
        instructions = file.read()

    # Combine prompt and instructions
    combined_prompt = f"{instructions}\n{args.prompt}"

    # Generate the payload
    headers, payload = generate_payload(args.api_key, combined_prompt)

    # Send request to OpenAI API
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    response_json = response.json()

    # Check for errors in the response
    if 'error' in response_json:
        print(f"API Error: {response_json['error']['message']}")
        return

    # Validate 'choices' key
    if 'choices' not in response_json or not response_json['choices']:
        print("Error: Unexpected response structure (missing 'choices'):", response_json)
        return

    # Extract assistant's response safely
    assistant_message = response_json['choices'][0].get('message', {})

    if 'content' not in assistant_message:
        print("Error: Missing 'content' field in API response:", response_json)
        return

    assistant_content = assistant_message['content'].strip()

    # Step 1: Remove Markdown ```json``` decorations if present
    assistant_content = remove_markdown_backticks(assistant_content)

    # Debug: Print cleaned API response
    print("Raw API Response:", assistant_content)

    # Step 2: Try parsing normally
    try:
        assistant_content_json = json.loads(assistant_content)
    except json.JSONDecodeError:
        print("First JSON parse failed. Trying smart auto-fix...")

        fixed_content = smart_clean_json_response(assistant_content)

        try:
            assistant_content_json = json.loads(fixed_content)
            print("Smart auto-fix succeeded.")
        except json.JSONDecodeError:
            print("Smart auto-fix failed. JSON still invalid.")
            return

    # Step 3: Handle if response is double-wrapped
    if isinstance(assistant_content_json, dict) and "content" in assistant_content_json:
        inner_content = assistant_content_json["content"]
        try:
            assistant_content_json = json.loads(inner_content)
        except json.JSONDecodeError:
            print("Warning: Second level JSON parsing failed. Keeping original.")

    # Step 4: Save to output file
    with open(args.output_path, 'w') as json_file:
        json.dump(assistant_content_json, json_file, indent=4)

    print(f"Extracted response saved to {args.output_path}")

if __name__ == "__main__":
    main()
