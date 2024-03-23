import os
import re
import sys
import json
import torch
from PIL import Image, ImageOps
from PIL.PngImagePlugin import PngInfo
import numpy as np
import locale
from datetime import datetime
from pathlib import Path
import hashlib

from impact.utils import *

# NOTE: this should not be `from . import core`.
# I don't know why but... 'from .' and 'from impact' refer to different core modules.
# This separates global variables of the core module and breaks the preview bridge.
from impact import core
# <--
import random


sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))
original_locale = locale.setlocale(locale.LC_TIME, "")

import folder_paths


class SaveImageStatic:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "filepath": ("STRING", {"forceInput": True}),
                "filename": ("STRING", {"default": ""}),
                "image_preview": (["disabled", "enabled"], {"default": "enabled"}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "image"

    def get_subfolder_path(self, image_path):
        image_path = Path(image_path).resolve()
        output_path = Path(self.output_dir).resolve()
        relative_path = image_path.relative_to(output_path)
        subfolder_path = relative_path.parent

        return str(subfolder_path)

    def save_images(self, images, filepath, filename, image_preview):
        full_file_path = os.path.join(filepath, filename)
        results = list()
        for batch_number, image in enumerate(images):
            i = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            metadata = None
            img.save(
                full_file_path, pnginfo=metadata, compress_level=self.compress_level
            )

            if image_preview == "enabled":
                results.append(
                    {
                        "filename": filename,
                        "subfolder": self.get_subfolder_path(full_file_path),
                        "type": self.type,
                    }
                )

        return {"ui": {"images": results}}


class LoadImageStatic:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "filepath": ("STRING", {"forceInput": True}),
                "filename": ("STRING", {}),
            }
        }

    CATEGORY = "image"

    RETURN_TYPES = ("IMAGE", "MASK")
    FUNCTION = "load_image"

    def load_image(self, filepath, filename):
        image_path = LoadImageStatic._resolve_path(os.path.join(filepath, filename))

        i = Image.open(image_path)
        i = ImageOps.exif_transpose(i)
        image = i.convert("RGB")
        image = np.array(image).astype(np.float32) / 255.0
        image = torch.from_numpy(image)[None,]
        if "A" in i.getbands():
            mask = np.array(i.getchannel("A")).astype(np.float32) / 255.0
            mask = 1.0 - torch.from_numpy(mask)
        else:
            mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")
        return (image, mask)

    def _resolve_path(image) -> Path:
        image_path = Path(folder_paths.get_annotated_filepath(image))
        return image_path

    @classmethod
    def IS_CHANGED(s, filepath, filename, image_preview):
        image_path = LoadImageStatic._resolve_path(os.path.join(filepath, filename))
        m = hashlib.sha256()
        with open(image_path, "rb") as f:
            m.update(f.read())
        return m.digest().hex()


class RestoreSizeByBounds:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(self):
        return {
            "required": {
                "image": ("IMAGE",),
                "child_bounds": ("IMAGE_BOUNDS",),
                "parent_bounds": ("IMAGE_BOUNDS",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "restore_size"

    CATEGORY = "image"

    def tensor_to_pil(self, tensor):
        """Assumes tensor is in CxHxW format"""
        return Image.fromarray(tensor.numpy().astype("uint8").transpose(1, 2, 0))

    def pil_to_tensor(self, pil_img):
        """Convert PIL image to tensor in CxHxW format"""
        return torch.tensor(np.array(pil_img)).permute(2, 0, 1).float()

    def resize_image(self, image, target_size):
        """Resize image to target size (width, height)"""
        return image.resize(target_size, Image.ANTIALIAS)

    def restore_size(self, image, child_bounds, parent_bounds):
        # Convert tensor to PIL image
        pil_image = self.tensor_to_pil(image)

        # Calculate new size from child bounds
        child_size = (
            child_bounds[3] - child_bounds[2] + 1,
            child_bounds[1] - child_bounds[0] + 1,
        )

        # Resize image to the size of the child bounds
        resized_image = self.resize_image(pil_image, child_size)

        # Create a new blank image using parent bounds
        parent_size = (
            parent_bounds[3] - parent_bounds[2] + 1,
            parent_bounds[1] - parent_bounds[0] + 1,
        )
        blank_image = Image.new("RGB", parent_size, (255, 255, 255))

        # Calculate the position where the child image will be pasted in the parent image
        # Based on the upper-left corner of the child bounds
        paste_position = (child_bounds[2], child_bounds[0])

        # Paste the resized image onto the blank parent image
        blank_image.paste(resized_image, paste_position)

        # Convert back to tensor and return
        return (self.pil_to_tensor(blank_image),)


NODE_CLASS_MAPPINGS = {
    "RestoreSizeByBounds": RestoreSizeByBounds,
    "SaveImageStatic": SaveImageStatic,
    "LoadImageStatic": LoadImageStatic,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RestoreSizeByBounds": "Restore Size By Bounds",
    "SaveImageStatic": "Save Image Static",
    "LoadImageStatic": "Load Image Static",
}
