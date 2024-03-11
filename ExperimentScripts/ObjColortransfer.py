import pymeshlab

def main():

    # create a new MeshSet
    ms = pymeshlab.MeshSet()

    ms.load_new_mesh("./20240229125610_scaned_target.obj")

    ms.generate_voronoi_atlas_parametrization(overlapflag=True)
    ms.transfer_vertex_attributes_to_texture_1_or_2_meshes(sourcemesh=0, targetmesh=1, textname="20240229125610_scaned_target.png")

    # ms.parametrization_trivial_per_triangle(border=0.5)
    # ms.transfer_vertex_color_to_texture(textname="frag_2.png")

    ms.set_current_mesh(0)
    ms.save_current_mesh("20240229125610_scaned_target_2.obj")


if __name__ == "__main__":
    main()