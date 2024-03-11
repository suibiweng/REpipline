

# Python program to read
# json file

from itertools import chain
import json
import sys
 

path = sys.argv[1]
# Opening myfile.txt
f = open(path+'/myfile.txt')

# Data to be written
dictionary = {
    "frames":[]
}
imgDir = f.readline()

while imgDir:
    imgDir = "images/frame_"+imgDir
    imgDir = imgDir[:-1]
    imgId = imgDir[:-4]
    idLen = len(imgId)
    imgId = int(imgId[idLen-5:])
    print(imgId)
    imgMatrix = []
    for i in range(4):
        m =  list(map(float, f.readline().split()))
        imgMatrix.append(m)
    obj = {
        "file_path" : imgDir,
        "transform_matrix" : imgMatrix,
        "colmap_im_id": imgId
        }
    dictionary["frames"].append(obj)
    imgDir = f.readline()


json_object = json.dumps(dictionary, indent=4)
# print(json_object)
with open(path+"/transforms.json", "w") as outfile:
    outfile.write(json_object)

outfile.close()
 
# Closing file
f.close()