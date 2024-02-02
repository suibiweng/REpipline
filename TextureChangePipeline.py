import yaml

def generate_yaml(data):
    try:
        yaml_content = yaml.dump(data, default_flow_style=False)
        return yaml_content
    except Exception as e:
        print(f"Error generating YAML: {e}")
        return None

def save_to_yaml(yaml_content, filename='output.yaml'):
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
            'text': text,
            'append_direction': append_direction,
            'shape_path': shape_path
        },
        'optim': {
            'seed': seed
        }
    }

if __name__ == "__main__":
    # Create initial example_data with parameters
    initial_exp_name = 'The_Cup_2'
    initial_text = 'A Wood Cup, {} view'
    initial_append_direction = True
    initial_shape_path = 'shapes/Cup.obj'
    initial_seed = 3

    example_data = create_example_data(
        exp_name=initial_exp_name,
        text=initial_text,
        append_direction=initial_append_direction,
        shape_path=initial_shape_path,
        seed=initial_seed
    )

    # Generate YAML
    yaml_content = generate_yaml(example_data)

    # Save YAML to a file
    if yaml_content:
        save_to_yaml(yaml_content, filename='output.yaml')
