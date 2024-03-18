import pymeshlab
import os
import sys

def process_obj_and_save(input_obj_path, output_folder):
    base_name = os.path.splitext(os.path.basename(input_obj_path))[0]
    output_folder = os.path.join(output_folder, base_name)
    
    os.makedirs(output_folder, exist_ok=True)
    
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(input_obj_path)
    
    # Merge close vertices
    p = pymeshlab.PercentageValue(1)
    ms.meshing_merge_close_vertices(threshold=p)
    
    # Remove isolated pieces
    p = pymeshlab.PercentageValue(90)
    ms.meshing_remove_connected_component_by_diameter(mincomponentdiag=p)
    
    #simplify
    ms.meshing_decimation_quadric_edge_collapse(targetfacenum = 250000)    
    
    
    #smooth
    
    ms.apply_coord_laplacian_smoothing(stepsmoothnum =3)
    
    
    
    # Apply trivial per-triangle parameterization
    ms.compute_texcoord_parametrization_triangle_trivial_per_wedge(sidedim=0, textdim=1024, border=0, method='Basic')
    
    # Transfer vertex attributes to texture
    ms.compute_texmap_from_color(textname="1.png", textw=1024, texth=1024)
    
    processed_obj_path = os.path.join(output_folder, base_name + '.obj')
    ms.save_current_mesh(processed_obj_path)
    
    return output_folder

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <path_to_input_OBJ_file> <output_path>")
        sys.exit(1)
    
    input_obj_path = sys.argv[1]
    output_path = sys.argv[2]
    folder_path = process_obj_and_save(input_obj_path, output_path)
    print(f"Processed files are saved in: {folder_path}")
