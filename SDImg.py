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


def call_txt2img_api(server_url, prompt, output_file_name, **kwargs):
    payload = {
        "prompt": prompt,
        "negative_prompt": kwargs.get("negative_prompt", ""),
        "seed": kwargs.get("seed", 1),
        "steps": kwargs.get("steps", 20),
        "width": kwargs.get("width", 512),
        "height": kwargs.get("height", 512),
        "cfg_scale": kwargs.get("cfg_scale", 7),
        "sampler_name": kwargs.get("sampler_name", "DPM++ 2M"),
        "n_iter": kwargs.get("n_iter", 1),
        "batch_size": kwargs.get("batch_size", 1),
    }
    response = call_api(server_url, 'sdapi/v1/txt2img', **payload)
    for index, image in enumerate(response.get('images')):
        save_path = f"{output_file_name}-{timestamp()}-{index}.png"
        decode_and_save_base64(image, save_path)


def call_img2img_api(server_url, input_image, prompt, output_file_name, mask_image=None, **kwargs):
    init_images = [encode_file_to_base64(input_image)]
    payload = {
        "prompt": prompt,
        "seed": kwargs.get("seed", 1),
        "steps": kwargs.get("steps", 20),
        "width": kwargs.get("width", 512),
        "height": kwargs.get("height", 512),
        "denoising_strength": kwargs.get("denoising_strength", 0.5),
        "n_iter": kwargs.get("n_iter", 1),
        "init_images": init_images,
        "batch_size": len(init_images),
        "resize_mode": 0
    }
    # if mask_image:
    #     payload["mask"] = encode_file_to_base64(mask_image)
      
    #     payload["cfg_scale"] = 1.5
    #     payload["denoising_strength"] = 0.75
        
        
        
    #     payload["mask_blur_x"] = 4
    #     payload["mask_blur_y"] = 4
    #     # payload["mask_blur_y"]
    #     payload["mask_blur"] = 4
        
    #     payload["initial_noise_multiplier"]=1
    #     # payload ["mask_transparency"]=0
    #     payload["inpainting_fill"] = 1
    #     # payload["inpaint_full_res"]= 0
    #     payload["inpaint_full_res_padding"]= 32
    #     # payload["inpainting_mask_invert"]= 0

    if mask_image:
        payload["mask"] = encode_file_to_base64(mask_image)
        payload["cfg_scale"] = 1.5
        payload["denoising_strength"] = 0.75
        payload["mask_blur_x"] = 4
        payload["mask_blur_y"] = 4
        payload["mask_blur"] = 4
        payload["mask_round"] = True
        payload["inpainting_mask_invert"] = 0
        payload["inpaint_full_res"] = 0
        payload["inpaint_full_res_padding"] = 32
        payload["initial_noise_multiplier"] = 1
        payload["inpainting_fill"] = kwargs.get("inpainting_mode", 0)
        

        






#   "mask_blur_x": 4,
#   "mask_blur_y": 4,
#   "mask_blur": 0,
#   "mask_round": true,
#   "inpainting_fill": 0,
#   "inpaint_full_res": true,
#   "inpaint_full_res_padding": 0,
#   "inpainting_mask_invert": 0,





    response = call_api(server_url, 'sdapi/v1/img2img', **payload)
    for index, image in enumerate(response.get('images')):
        save_path = f"{output_file_name}.png"
        decode_and_save_base64(image, save_path)


def process_request(server_url, output_file_name, mode, prompt=None, input_image=None, mask_image=None, **kwargs):
    if mode == 'txt2img':
        if not prompt:
            raise ValueError("The 'prompt' argument is required for txt2img mode.")
        call_txt2img_api(server_url, prompt, output_file_name, **kwargs)
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
