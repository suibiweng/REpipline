import torch
import os
import zipfile
import pymeshlab
from shap_e.diffusion.sample import sample_latents
from shap_e.diffusion.gaussian_diffusion import diffusion_from_config
from shap_e.models.download import load_model, load_config
from shap_e.util.notebooks import decode_latent_mesh

# Initialize device (CUDA if available)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

# Load models
xm = load_model('transmitter', device=device)
model = load_model('text300M', device=device)
diffusion = diffusion_from_config(load_config('diffusion'))

def ShapEgeneratemodel(prompt, urid):
    """Generate a 3D model from text and return the output file path."""
    return generate(prompt, 24, 60, 'obj', urid)

def generate(prompt, cfg, steps, fileFormat, filename):
    """Generate a 3D model using Shap-E and save it in the specified format."""
    latents = sample_latents(
        batch_size=1,
        model=model,
        diffusion=diffusion,
        guidance_scale=int(cfg),
        model_kwargs=dict(texts=[prompt]),
        progress=True,
        clip_denoised=True,
        use_fp16=True,
        use_karras=True,
        karras_steps=int(steps),
        sigma_min=1E-3,
        sigma_max=160,
        s_churn=0,
    )

    # Decode and save the mesh
    for i, latent in enumerate(latents):
        t = decode_latent_mesh(xm, latent).tri_mesh()
        with open('plyFile.ply', 'wb') as f:
            t.write_ply(f)

    export_file('plyFile.ply', f'{filename}.{fileFormat}', fileFormat, filename)
    
    return f"{filename}.{fileFormat}"

def export_file(input_file, output_file, output_format, urlid):
    """Convert and export a mesh file to the specified format and create a ZIP."""
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(input_file)

    # Check if vertex colors exist
    if not ms.current_mesh().has_vertex_color():
        print("Warning: Mesh does not have vertex colors!")

    # Export options
    export_options = {
        "save_vertex_color": True,
        "save_face_color": True,
        "save_wedge_texcoord": True
    }

    if output_format in ["ply", "glb", "gltf"]:
        ms.save_current_mesh(output_file, **export_options)
    elif output_format == "obj":
        print("Warning: OBJ format does not support vertex colors natively.")
        ms.save_current_mesh(output_file, save_vertex_color=True)
    elif output_format == "fbx":
        ms.save_current_mesh(output_file, **export_options)
    elif output_format == "blend":
        print("PyMeshLab does not support exporting to .blend format.")
        return
    else:
        print("Invalid output file format.")
        return

    # Create ZIP file
    zip_file = f"{urlid}_ShapE.zip"
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(output_file, os.path.basename(output_file))

    print(f"Exported and zipped: {zip_file}")
