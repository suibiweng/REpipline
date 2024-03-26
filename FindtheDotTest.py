import argparse
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# Set up argument parsing
parser = argparse.ArgumentParser(description='Display an image with a dot at given coordinates.')
parser.add_argument('filename', type=str, help='Path to the image file.')
parser.add_argument('coordinates', type=str, help='Coordinates where to place the dot, in "x,y" format.')
args = parser.parse_args()

# Convert the coordinates from string to a list of integers
coordinates = list(map(int, args.coordinates.split(',')))

def show_image(filename, coordinates):
    plt.clf()  # Clear the current figure
    
    # Load and display the image
    img = mpimg.imread(filename)
    plt.imshow(img)
    plt.scatter([coordinates[0]], [coordinates[1]+125], color='white')  # Draw a red dot
    
    plt.show()

# Call the function with arguments
show_image(args.filename, coordinates)