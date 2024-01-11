# GPT-4 Image Labeller

This Python script uses the GPT-4 Vision API to label images in a specified directory and sort them into subdirectories based on their labels.

## Prerequisites

- Python 3.6 or higher
- OpenAI API key
- aiohttp library
- configparser library
- glob library
- logging library
- openai library
- requests library
- shutil library

## Installation

1. Clone the repository.
2. Install the required Python libraries using pip:
```pip3 install -r requirements.txt```

## Configuration

1. Open the `config.ini` file.
2. Set the `API_KEY` under the OpenAI section to your OpenAI API key.
3. Set the `SOURCE_DIRECTORY` under the Directories section to the root source directory for your images.

## Usage

1. Run the script using Python:

```python3 main.py```

The script will find all images in the source directory and its subdirectories, send them to the OpenAI API for labelling, and then sort them into subdirectories in a "sorted" directory within the source directory based on their labels.

By default, the script will ask for confirmation before sending the images to OpenAI for labelling, print the path of every image it finds, and delete the original images after copying them to the sorted directory. These behaviors can be changed by modifying the arguments to the label_and_move_images function call in the if __name__ == "__main__": block.

This project is licensed under the terms of the MIT license.