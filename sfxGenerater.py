import argparse
from elevenlabs import ElevenLabs

def generate_sound_from_text(text_input, filename):
    # Initialize the client
    client = ElevenLabs(
        api_key="sk_8dd876631a5ab89fb614c3b676ecf9de3c6410133bacf63c",
    )

    # Generate the sound from text input
    sound_data = client.text_to_sound_effects.convert(
        text=text_input,
        duration_seconds=0.5,
        prompt_influence=0.8,
    )

    # Open the file and write data in chunks
    with open(filename, 'wb') as f:
        for chunk in sound_data:
            f.write(chunk)

    print(f"Sound generated and saved as {filename}")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Generate sound from text and save as a file.")
    parser.add_argument("input_text", type=str, help="The text to generate sound from.")
    parser.add_argument("file_name", type=str, help="The output file name (e.g., output.wav).")

    # Parse arguments
    args = parser.parse_args()

    # Ensure the file name has the .wav extension
    if not args.file_name.endswith(".wav"):
        args.file_name += ".wav"

    # Generate sound based on the arguments
    generate_sound_from_text(args.input_text, args.file_name)
