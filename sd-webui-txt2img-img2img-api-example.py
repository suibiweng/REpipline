from datetime import datetime
import urllib.request
import base64
import json
import time
import os

webui_server_url = 'http://127.0.0.1:7862'

out_dir = 'api_out'
out_dir_t2i = os.path.join(out_dir, 'txt2img')
out_dir_i2i = os.path.join(out_dir, 'img2img')
os.makedirs(out_dir_t2i, exist_ok=True) 
os.makedirs(out_dir_i2i, exist_ok=True)


def timestamp():
    return datetime.fromtimestamp(time.time()).strftime("%Y%m%d-%H%M%S")


def encode_file_to_base64(path):
    with open(path, 'rb') as file:
        return base64.b64encode(file.read()).decode('utf-8')


def decode_and_save_base64(base64_str, save_path):
    with open(save_path, "wb") as file:
        file.write(base64.b64decode(base64_str))


def call_api(api_endpoint, **payload):
    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        f'{webui_server_url}/{api_endpoint}',
        headers={'Content-Type': 'application/json'},
        data=data,
    )
    response = urllib.request.urlopen(request)
    return json.loads(response.read().decode('utf-8'))


def call_txt2img_api(**payload):
    response = call_api('sdapi/v1/txt2img', **payload)
    for index, image in enumerate(response.get('images')):
        save_path = os.path.join(out_dir_t2i, f'txt2img-{timestamp()}-{index}.png')
        decode_and_save_base64(image, save_path)


def call_img2img_api(**payload):
    response = call_api('sdapi/v1/img2img', **payload)
    for index, image in enumerate(response.get('images')):
        save_path = os.path.join(out_dir_i2i, f'img2img-{timestamp()}-{index}.png')
        decode_and_save_base64(image, save_path)
        
        







if __name__ == '__main__':
    payload = {
        "prompt": "ugly Capybaras in a pool",  # extra networks also in prompts
        "negative_prompt": "",
        "seed": 1,
        "steps": 20,
        "width": 512,
        "height": 512,
        "cfg_scale": 7,
        "sampler_name": "DPM++ 2M",
        "n_iter": 1,
        "batch_size": 1,

        # example args for x/y/z plot
        # "script_name": "x/y/z plot",
        # "script_args": [
        #     1,
        #     "10,20",
        #     [],
        #     0,
        #     "",
        #     [],
        #     0,
        #     "",
        #     [],
        #     True,
        #     True,
        #     False,
        #     False,
        #     0,
        #     False
        # ],

        # example args for Refiner and ControlNet
        # "alwayson_scripts": {
        #     "ControlNet": {
        #         "args": [
        #             {
        #                 "batch_images": "",
        #                 "control_mode": "Balanced",
        #                 "enabled": True,
        #                 "guidance_end": 1,
        #                 "guidance_start": 0,
        #                 "image": {
        #                     "image": encode_file_to_base64(r"B:\path\to\control\img.png"),
        #                     "mask": None  # base64, None when not need
        #                 },
        #                 "input_mode": "simple",
        #                 "is_ui": True,
        #                 "loopback": False,
        #                 "low_vram": False,
        #                 "model": "control_v11p_sd15_canny [d14c016b]",
        #                 "module": "canny",
        #                 "output_dir": "",
        #                 "pixel_perfect": False,
        #                 "processor_res": 512,
        #                 "resize_mode": "Crop and Resize",
        #                 "threshold_a": 100,
        #                 "threshold_b": 200,
        #                 "weight": 1
        #             }
        #         ]
        #     },
        #     "Refiner": {
        #         "args": [
        #             True,
        #             "sd_xl_refiner_1.0",
        #             0.5
        #         ]
        #     }
        # },
        # "enable_hr": True,
        # "hr_upscaler": "R-ESRGAN 4x+ Anime6B",
        # "hr_scale": 2,
        # "denoising_strength": 0.5,
        # "styles": ['style 1', 'style 2'],
        # "override_settings": {
        #     'sd_model_checkpoint': "sd_xl_base_1.0",  # this can use to switch sd model
        # },
    }
    call_txt2img_api(**payload)

    init_images = [
        encode_file_to_base64(r"B:\path\to\img_1.png"),
        # encode_file_to_base64(r"B:\path\to\img_2.png"),
        # "https://image.can/also/be/a/http/url.png",
    ]

    batch_size = 2
    payload = {
        "prompt": "1girl, blue hair",
        "seed": 1,
        "steps": 20,
        "width": 512,
        "height": 512,
        "denoising_strength": 0.5,
        "n_iter": 1,
        "init_images": init_images,
        "batch_size": batch_size if len(init_images) == 1 else len(init_images),
        # "mask": encode_file_to_base64(r"B:\path\to\mask.png")
    }
    
    call_img2img_api(**payload)
    
    
    
#     {
#   "prompt": "",
#   "negative_prompt": "",
#   "styles": [
#     "string"
#   ],
#   "seed": -1,
#   "subseed": -1,
#   "subseed_strength": 0,
#   "seed_resize_from_h": -1,
#   "seed_resize_from_w": -1,
#   "sampler_name": "string",
#   "scheduler": "string",
#   "batch_size": 1,
#   "n_iter": 1,
#   "steps": 50,
#   "cfg_scale": 7,
#   "width": 512,
#   "height": 512,
#   "restore_faces": true,
#   "tiling": true,
#   "do_not_save_samples": false,
#   "do_not_save_grid": false,
#   "eta": 0,
#   "denoising_strength": 0.75,
#   "s_min_uncond": 0,
#   "s_churn": 0,
#   "s_tmax": 0,
#   "s_tmin": 0,
#   "s_noise": 0,
#   "override_settings": {},
#   "override_settings_restore_afterwards": true,
#   "refiner_checkpoint": "string",
#   "refiner_switch_at": 0,
#   "disable_extra_networks": false,
#   "firstpass_image": "string",
#   "comments": {},
#   "init_images": [
#     "string"
#   ],
#   "resize_mode": 0,
#   "image_cfg_scale": 0,
#   "mask": "string",
#   "mask_blur_x": 4,
#   "mask_blur_y": 4,
#   "mask_blur": 0,
#   "mask_round": true,
#   "inpainting_fill": 0,
#   "inpaint_full_res": true,
#   "inpaint_full_res_padding": 0,
#   "inpainting_mask_invert": 0,
#   "initial_noise_multiplier": 0,
#   "latent_mask": "string",
#   "force_task_id": "string",
#   "sampler_index": "Euler",
#   "include_init_images": false,
#   "script_name": "string",
#   "script_args": [],
#   "send_images": true,
#   "save_images": false,
#   "alwayson_scripts": {},
#   "infotext": "string"
# }
    
    
    
    
    
    # # if len(init_images) > 1 then batch_size should be == len(init_images)
    # # else if len(init_images) == 1 then batch_size can be any value int >= 1
    # call_img2img_api(**payload)

    # there exist a useful extension that allows converting of webui calls to api payload
    # particularly useful when you wish setup arguments of extensions and scripts
    # https://github.com/huchenlei/sd-webui-api-payload-display