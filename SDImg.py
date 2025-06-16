from datetime import datetime
import urllib.request
import base64
import json
import time
import os
import argparse


def timestamp():
    return datetime.fromtimestamp(time.time()).strftime("%Y%m%d-%H%M%S")


def encode_file_to_base64(path):
    with open(path, 'rb') as file:
        return base64.b64encode(file.read()).decode('utf-8')


def decode_and_save_base64(base64_str, save_path):
    with open(save_path, "wb") as file:
        file.write(base64.b64decode(base64_str))


def call_api(server_url, api_endpoint, **payload):
    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        f'{server_url}/{api_endpoint}',
        headers={'Content-Type': 'application/json'},
        data=data,
    )
    response = urllib.request.urlopen(request)
    return json.loads(response.read().decode('utf-8'))


def call_img2img_api(server_url, input_image, prompt, output_file_name, mask_image=None, **kwargs):
    # Encode the input image as base64.
    init_image = encode_file_to_base64(input_image)
    

    if mask_image is None:
        # Use the full payload as given
        payload = {
            "alwayson_scripts": {
                "API payload": {"args": []},
                "Comments": {"args": []},
                "Extra options": {"args": []},
                "Hypertile": {"args": []},
                "Refiner": {"args": [False, "", 0.8]},
                "Sampler": {"args": [20, "DPM++ 2M", "Automatic"]},
                "Seed": {"args": [-1, False, -1, 0, 0, 0]},
                "Soft Inpainting": {"args": [False, 1, 0.5, 4, 0, 0.5, 2]}
            },
            "batch_size": 1,
            "cfg_scale": 7,
            "comments": {},
            "denoising_strength": 0.75,
            "disable_extra_networks": False,
            "do_not_save_grid": False,
            "do_not_save_samples": False,
            "height": 960,
            "image_cfg_scale": 1.5,
            "init_images": [init_image],
            "initial_noise_multiplier": 1.0,
            "inpaint_full_res": 0,
            "inpaint_full_res_padding": 32,
            "inpainting_fill": 1,
            "inpainting_mask_invert": 0,
            "mask_blur": 4,
            "mask_blur_x": 4,
            "mask_blur_y": 4,
            "mask_round": True,
            "n_iter": 1,
            "negative_prompt": "",
            "override_settings": {},
            "override_settings_restore_afterwards": True,
            "prompt": prompt,
            "resize_mode": 0,
            "restore_faces": False,
            "s_churn": 0.0,
            "s_min_uncond": 0.0,
            "s_noise": 1.0,
            "s_tmax": None,
            "s_tmin": 0.0,
            "sampler_name": "DPM++ 2M",
            "scheduler": "Automatic",
            "script_args": [],
            "script_name": None,
            "seed": -1,
            "seed_enable_extras": True,
            "seed_resize_from_h": -1,
            "seed_resize_from_w": -1,
            "steps": kwargs.get("steps", 20),
            "styles": [],
            "subseed": -1,
            "subseed_strength": 0,
            "tiling": False,
            "width": 1280
        }
    else:
        payload = {
    "alwayson_scripts": {
        "API payload": {"args": []},
        "Comments": {"args": []},
        "Extra options": {"args": []},
        "Hypertile": {"args": []},
        "Refiner": {"args": [False, "", 0.8]},
        "Sampler": {"args": [20, "DPM++ 2M", "Automatic"]},
        "Seed": {"args": [-1, False, -1, 0, 0, 0]},
        "Soft Inpainting": {"args": [False, 1, 0.5, 4, 0, 0.5, 2]}
    },
    "batch_size": 1,
    "cfg_scale": 10,
    "comments": {},
    "denoising_strength": 0.9,  # Low to preserve Ironman face
    "disable_extra_networks": False,
    "do_not_save_grid": False,
    "do_not_save_samples": False,
    "height": 960,
    "image_cfg_scale": 1.5,
    "init_images": [init_image],  # ← base64-encoded image (Ironman face + hat stroke)
    "mask": encode_file_to_base64(mask_image),  # ← base64-encoded binary mask (white = hat area only)
    "initial_noise_multiplier": 1.0,
    "inpaint_full_res": 1,
    "inpaint_full_res_padding": 32,
    "inpainting_fill": 1,
    "inpainting_mask_invert": 0,
    "mask_blur": 2,
    "mask_blur_x": 4,
    "mask_blur_y": 4,
    "mask_round": False,
    "n_iter": 1,
    "negative_prompt": "",
    "override_settings": {},
    "override_settings_restore_afterwards": True,
    "prompt": prompt,  # e.g., "a cartoon-style top hat"
    "resize_mode": 0,
    "restore_faces": False,
    "s_churn": 0.0,
    "s_min_uncond": 0.0,
    "s_noise": 1.0,
    "s_tmax": None,
    "s_tmin": 0.0,
    "sampler_name": "DPM++ 2M",
    "scheduler": "Automatic",
    "script_args": [],
    "script_name": None,
    "seed": -1,
    "seed_enable_extras": True,
    "seed_resize_from_h": -1,
    "seed_resize_from_w": -1,
    "steps": 50,
    "styles": [],
    "subseed": -1,
    "subseed_strength": 0,
    "tiling": False,
    "width": 1280
    }





        # payload = {
        #     "prompt": prompt,
        #     "seed": kwargs.get("seed", 1),
        #     "steps": kwargs.get("steps", 20),
        #     "width": kwargs.get("width", 512),
        #     "height": kwargs.get("height", 512),
        #     "denoising_strength": kwargs.get("denoising_strength", 0.5),
        #     "n_iter": kwargs.get("n_iter", 1),
        #     "init_images": [init_image],
        #     "batch_size": 1,
        #     "resize_mode": 0,
        #     "mask": encode_file_to_base64(mask_image),
        #     "cfg_scale": 1.5,
        #     "denoising_strength": 0.75,
        #     "mask_blur_x": 4,
        #     "mask_blur_y": 4,
        #     "mask_blur": 4,
        #     "mask_round": True,
        #     "inpainting_mask_invert": 0,
        #     "inpaint_full_res": 0,
        #     "inpaint_full_res_padding": 32,
        #     "initial_noise_multiplier": 1,
        #     "inpainting_fill": 1
        # }
    
    # Call the API with the constructed payload.
    response = call_api(server_url, 'sdapi/v1/img2img', **payload)
    for index, image in enumerate(response.get('images', [])):
        save_path = f"{output_file_name}.png"
        decode_and_save_base64(image, save_path)


def process_request(server_url, output_file_name, mode, prompt=None, input_image=None, mask_image=None, **kwargs):
    if mode == 'txt2img':
        if not prompt:
            raise ValueError("The 'prompt' argument is required for txt2img mode.")
        # call_txt2img_api(server_url, prompt, output_file_name, **kwargs)
    elif mode == 'img2img':
        if not input_image or not prompt:
            raise ValueError("Both 'input_image' and 'prompt' are required for img2img mode.")
        call_img2img_api(server_url, input_image, prompt, output_file_name, mask_image, **kwargs)
    else:
        raise ValueError("Invalid mode. Use 'txt2img' or 'img2img'.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Call txt2img or img2img API.")
    parser.add_argument("--server_url", type=str, required=True, help="URL of the server (e.g., http://127.0.0.1:7862).")
    parser.add_argument("--output_file_name", type=str, required=True, help="Base name for the output files.")
    parser.add_argument("--mode", type=str, required=True, choices=["txt2img", "img2img"], help="Mode of the API ('txt2img' or 'img2img').")
    parser.add_argument("--prompt", type=str, required=True, help="Text prompt for the API.")
    parser.add_argument("--input_image", type=str, help="Path to the input image (required for img2img).")
    parser.add_argument("--mask_image", type=str, help="Path to the mask image (optional for img2img).")
    parser.add_argument("--seed", type=int, default=1, help="Seed for the image generation.")
    parser.add_argument("--steps", type=int, default=20, help="Number of steps for generation.")
    parser.add_argument("--width", type=int, default=512, help="Width of the generated image.")
    parser.add_argument("--height", type=int, default=512, help="Height of the generated image.")
    parser.add_argument("--cfg_scale", type=float, default=7.0, help="CFG scale for image generation.")
    parser.add_argument("--denoising_strength", type=float, default=0.5, help="Denoising strength (for img2img).")
    parser.add_argument("--inpainting_mode", type=int, default=0, help="")
    args = parser.parse_args()

    process_request(
        server_url=args.server_url,
        output_file_name=args.output_file_name,
        mode=args.mode,
        prompt=args.prompt,
        input_image=args.input_image,
        mask_image=args.mask_image,
        seed=args.seed,
        steps=args.steps,
        width=args.width,
        height=args.height,
        cfg_scale=args.cfg_scale,
        denoising_strength=args.denoising_strength,
        inpainting_mode=args.inpainting_mode
    )
