import os
import glob
import configparser
import logging
import openai as OpenAI
import requests
import base64
import aiohttp
import random
import asyncio
import shutil
from aiohttp import client_exceptions

# Set up logging 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Read configuration
config = configparser.ConfigParser()
config.read('config.ini')
openai_api_key = config.get('OpenAI', 'API_KEY')
SOURCE_DIRECTORY = config.get('Directories', 'SOURCE_DIRECTORY')

IMAGE_LABEL_PROMPT = """
                Classify each image. 
                Delimit labels for the classification with _
                The first label should be one of the following primary labels
                Primary labels: ["Screenshot", "Photograph", "Meme", "Graphic", "Document", "Art", "Misc"]
                The second label should be the main label for what the image contains, 1-3 words
                For screenshots, the second label should be the program being used in the screenshot. The third label should describe what the program is doing or the general purpose of the program. Be as specific as possible so there is no ambiguity as to what being described
                For photographs the second label should be the setting of the photograph, and the third should be the subejct/additional details about it
                For graphics, the second label should be the main text in the graphic or a short name for it to describe its purpose, and the third label should be additional details
                In general the third label should cover the general idea or purpose of the image as descriptively as possible. If there is large text in the image, use that as part of the labelling if it is significant to the main purpose of the image
                Example label:
                Screenshot_Visual Studio Code_Python image classification program
                """


def find_images(directory):
    extensions = ['png', 'jpg', 'jpeg', 'gif', 'webp']
    files = []
    for ext in extensions:
        files.extend(glob.glob(f"{directory}/**/*.{ext}", recursive=True))
    return files


def encode_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to encode image {image_path}: {e}")
        return None


async def label_image_async(session, image_path, openai_api_key, max_retries=5, initial_delay=1.0):

    base64_image = encode_image(image_path)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
        {
            "role": "user",
            "content": [
            {
                "type": "text",
                "text": IMAGE_LABEL_PROMPT,
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": "low",
                }
            }
            ]
        }
        ],
        "max_tokens": 400,
    }

    # Use GPT-4 Turbo to label the image

    delay = initial_delay
    
    for attempt in range(max_retries):
        try:
            async with session.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                elif response.status == 429:
                    logger.warning("Rate limit error: backing off and retrying")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay + random.uniform(0, 1))
                        delay *= 2
                    else:
                        return f"Error: {response.status}"
        except client_exceptions.ServerDisconnectedError:
            logger.warning("Server disconnected: backing off and retrying")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay + random.uniform(0, 1))
                delay *= 2
            else:
                return f"Error: Server disconnected"


async def get_labels(image_files):
    labels = []
    async with aiohttp.ClientSession() as session:
        tasks = [label_image_async(session, image_file, openai_api_key) for image_file in image_files]
        labels = await asyncio.gather(*tasks)
    return labels


def validate_directory(directory):
    """Validate if the provided directory path exists and is a directory."""
    if not os.path.exists(directory):
        logger.error(f"Directory does not exist: {directory}")
        return False
    if not os.path.isdir(directory):
        logger.error(f"Provided path is not a directory: {directory}")
        return False
    return True


def sanitize_label(label):
    invalid_chars = ['/', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        label = label.replace(char, '_')
    return label


def label_and_move_images(src_path, ask_to_proceed=True, debug_output=False, keep_originals=False):
    logger.info(f"Searching for images in {src_path}")
    print(f"Searching for images in {src_path}")

    image_files = find_images(src_path)
    if debug_output:
        for file in image_files:
            print(f"Found file: {file}")

    num_images = len(image_files)
    num_input_tokens = num_images * 350  # Example calculation
    num_output_tokens = num_images * 10
    openai_price = num_input_tokens * 0.00001 + num_output_tokens * 0.00003
    print(f"Calculated cost: ${openai_price}")

    if ask_to_proceed:
        proceed = input(f"Found {num_images} images. Proceed with classification? (y/n) ")
        if proceed.lower() != 'y':
            return

    print("Labelling image files. This may take a while.")
    labels = asyncio.run(get_labels(image_files))

    print(f"Retrieved labels from OpenAI. Moving to sorted folder within {src_path}")
    dst_path = os.path.join(src_path, "sorted")
    os.makedirs(dst_path, exist_ok=True)

    for image, label in zip(image_files, labels):
        folder_name = label.split("_")[0]
        folder_path = os.path.join(dst_path, folder_name + "s")
        os.makedirs(folder_path, exist_ok=True)
        sanitized_label = sanitize_label(label[len(folder_name)+1:])
        shutil.copy(image, os.path.join(folder_path, sanitized_label) + "." + image.split(".")[-1])
        if not keep_originals:
            os.remove(image)  # Delete the original image
            
HOME = os.path.expanduser('~') # Home path

if __name__ == "__main__":

    if validate_directory(SOURCE_DIRECTORY):
        label_and_move_images(
            src_path=SOURCE_DIRECTORY,
            ask_to_proceed = True, # Ask user before requesting labels from OpenAI
            debug_output = True, # Print the path of every image it finds
            keep_originals = False # If true, copy images from src to dest, if false the original image is deleted
        )
    else:
        print("Invalid source directory. Please check the path and try again.")