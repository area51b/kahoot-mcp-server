from dotenv import load_dotenv
import os
import sys
import mss
import json
import requests
import keyboard
import pyautogui
import pytesseract
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

def get_env(var):
    value = os.getenv(var)
    if not value:
        raise EnvironmentError(f"Environment variable '{var}' is not set.")
    return value

# Set Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = get_env("TESSERACT_PATH")

def click_button(button):
    button_coords = {1: (0.25, 0.75), 2: (0.77, 0.75), 3: (0.25, 0.822), 4: (0.77, 0.822)}
    width, height = pyautogui.size()
    x, y = button_coords[button]
    pyautogui.click(int(width * x), int(height * y))
    pyautogui.click(int(width * x), int(height * y))

def nims_cloud_answer(text):
    url = get_env("NIMS_API_URL")
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {get_env('NIMS_API_KEY')}"
    }
    payload = {
        "model": "meta/llama-4-maverick-17b-128e-instruct",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant specialized in answering multiple-choice questions who only responds with the button number corresponding to the right answer, do not respond with words only a integer between 1 and 4 that corresponds to the answer."
            },
            {"role": "user", "content": text}
        ],
        "max_tokens": 512,
        "stream": False
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        reply = res.json()["choices"][0]["message"]["content"]
        return int(reply.strip())
    except Exception as e:
        print("Failed to get answer:", e)
        return None
    
def ollama_answer(question_and_answers):
    url = get_env("OLLAMA_API_URL")
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "llama3.3:70b-instruct-q4_0",
        #"model": "llama3.3:70b-instruct-fp16",
        #"model": "llama3.1:8b",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant specialized in answering multiple-choice questions who only responds with the button number corresponding to the right answer, do not respond with words only a integer between 1 and 4 that corresponds to the answer.",
            },
            {"role": "user", "content": question_and_answers},
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)

        # Extract the assistant's reply
        data = json.loads(response.text)
        reply = data["choices"][0]["message"]["content"]

        # Return the button number as an integer
        return int(reply)
    except ValueError:
        # Handle exception here if the reply is not an integer
        print(f"Unexpected reply: {reply}")
        return int(reply[1])
    except Exception as e:
        # Handle exception here if something else goes wrong
        print("Something went wrong.")
        print(e)
        print(response)
        return None

def preprocess_and_ocr(key, region):
    region = region.convert('L')
    if key == 0:
        region = region.point(lambda p: 255 if p > 180 else 0)
        config = '--oem 3 --psm 6'
    else:
        region = ImageEnhance.Contrast(region).enhance(3.0)
        region = region.filter(ImageFilter.SHARPEN)
        config = '--oem 3 --psm 7'
    region = region.resize((region.width * 2, region.height * 2))
    text = pytesseract.image_to_string(region, config=config)
    return key, text.strip()

def extract_text():
    print(f"[{datetime.now()}] extract_text triggered")

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')

    width, height = img.size
    coords = {
        0: {"top_left": (0.0, 0.58), "bottom_right": (1.0, 0.73)},
        1: {"top_left": (0.042, 0.725), "bottom_right": (0.458, 0.775)},
        2: {"top_left": (0.542, 0.725), "bottom_right": (1.0, 0.775)},
        3: {"top_left": (0.042, 0.795), "bottom_right": (0.458, 0.85)},
        4: {"top_left": (0.542, 0.795), "bottom_right": (1.0, 0.85)},
    }

    regions = {
        k: img.crop((
            int(width * v["top_left"][0]),
            int(height * v["top_left"][1]),
            int(width * v["bottom_right"][0]),
            int(height * v["bottom_right"][1])
        )) for k, v in coords.items()
    }

    result_text = ""
    with ThreadPoolExecutor() as pool:
        results = pool.map(lambda kv: preprocess_and_ocr(*kv), regions.items())
        for key, text in results:
            if text:
                line = f"Question: {text}" if key == 0 else f"{key}: {text}"
                result_text += line + "\n"

    print(result_text)

    try:
        #answer = nims_cloud_answer(result_text)
        answer = ollama_answer(result_text)
        print(f"Predicted answer: {answer}")
        if answer in [1, 2, 3, 4]:
            click_button(answer)
        else:
            click_button(1)
        print(f"[{datetime.now()}] click_button completed")
    except Exception as e:
        print("Error in answering/clicking:", e)

# Bind the function to a hotkey
keyboard.add_hotkey("ctrl+alt+t", extract_text)

# Keep the program running
try:
    keyboard.wait()
except KeyboardInterrupt:
    print("Program interrupted and exiting cleanly.")
