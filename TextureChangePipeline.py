import time
import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def generate_yaml(data):
    try:
        yaml_content = yaml.dump(data, default_flow_style=False)
        return yaml_content
    except Exception as e:
        print(f"Error generating YAML: {e}")
        return None

def save_to_yaml(yaml_content, filename='textures/output.yaml'):
    try:
        with open(filename, 'w') as file:
            file.write(yaml_content)
        print(f"YAML saved to {filename}")
    except Exception as e:
        print(f"Error saving YAML: {e}")

def create_example_data(exp_name, text, append_direction, shape_path, seed):
    return {
        'log': {
            'exp_name': exp_name
        },
        'guide': {
            'text':f'"{text}"',
            'append_direction': append_direction,
            'shape_path': shape_path
        },
        'optim': {
            'seed': seed
        }
    }

class MyHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        print(f"New file created: {event.src_path}")
        # Extract the file name from the path
        file_name = event.src_path.split("\\")[-1]

        # Use the file name in the variables
        updated_exp_name = file_name.split(".")[0]
        updated_shape_path = event.src_path
        print("file name-", updated_exp_name)
        print("file name-", updated_shape_path)

        # Create updated example_data with new file name and path
        updated_example_data = create_example_data(
            exp_name=updated_exp_name,
            text='A Wood Cup, {} view',
            append_direction=True,
            shape_path=updated_shape_path,
            seed=3
        )

        # Generate YAML
        yaml_content = generate_yaml(updated_example_data)

        # Save YAML to a file
        if yaml_content:
            save_to_yaml(yaml_content, filename='textures/output.yaml')

if __name__ == "__main__":

    # Watch for file changes
    folder_to_watch ="D:\\Desktop\\RealityEditor\\PythonProject\\TEXTurePaper\\Shapes_new"  # Replace with the actual folder path

    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path=folder_to_watch, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()




























# import yaml

# def generate_yaml(data):
#     try:
#         yaml_content = yaml.dump(data, default_flow_style=False)
#         return yaml_content
#     except Exception as e:
#         print(f"Error generating YAML: {e}")
#         return None

# def save_to_yaml(yaml_content, filename='output.yaml'):
#     try:
#         with open(filename, 'w') as file:
#             file.write(yaml_content)
#         print(f"YAML saved to {filename}")
#     except Exception as e:
#         print(f"Error saving YAML: {e}")

# def create_example_data(exp_name, text, append_direction, shape_path, seed):
#     return {
#         'log': {
#             'exp_name': exp_name
#         },
#         'guide': {
#             'text': text,
#             'append_direction': append_direction,
#             'shape_path': shape_path
#         },
#         'optim': {
#             'seed': seed
#         }
#     }

# if __name__ == "__main__":
#     # Create initial example_data with parameters
#     initial_exp_name = 'The_Cup_2'
#     initial_text = 'A Wood Cup, {} view'
#     initial_append_direction = True
#     initial_shape_path = 'shapes/Cup.obj'
#     initial_seed = 3

#     example_data = create_example_data(
#         exp_name=initial_exp_name,
#         text=initial_text,
#         append_direction=initial_append_direction,
#         shape_path=initial_shape_path,
#         seed=initial_seed
#     )

#     # Generate YAML
#     yaml_content = generate_yaml(example_data)

#     # Save YAML to a file
#     if yaml_content:
#         save_to_yaml(yaml_content, filename='textures/output.yaml')
