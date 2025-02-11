from flask import Flask, request, jsonify
from ShapEserver import ShapEgeneratemodel
import subprocess
app = Flask(__name__)

@app.route('/command', methods=['POST'])
def command():
    command = request.form.get('Command', 'No prompt provided')
    urlid = request.form.get('URLID', 'default')
    prompt = request.form.get('Prompt', '')

    if command == "IpcamCapture":
      
        print("")

    elif command == "ShapeE":
        
        ShapEgeneratemodel(urlid, prompt)
        print(f"ShapeE model generated successfully for URLID: {urlid}")
        return jsonify({"message": "ShapeE model generation started", "URLID": urlid, "Prompt": prompt}), 200
       

    elif command == "Story":
        call_OpenAI_script(prompt, f"{urlid}_StorySet.json","Story")


    else:
        return jsonify({"error": "Unknown command"}), 400






def call_OpenAI_script(prompt, output_path,instruction):
    global open_ai_key
    # Construct the command to call the external script
    command = [
        'python', 'send_openai_prompt.py',
        '--prompt', prompt,
        '--output_path', output_path,
        '--instructions_file', f'./PromptInstructions/{instruction}.txt'
    ]
    
    # Run the command using subprocess.Popen
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Communicate with the process to capture stdout and stderr
    stdout, stderr = process.communicate()
    
    # Print the output and errors (if any)
    print("STDOUT:", stdout)
    print("STDERR:", stderr)


if __name__ == '__main__':
    app.run(debug=True)
