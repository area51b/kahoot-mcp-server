from dotenv import load_dotenv
import os
import cv2
import mss
import json
import requests
import keyboard
import pyautogui
import pytesseract
import numpy as np
from datetime import datetime
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

def get_env(var):
    value = os.getenv(var)
    if not value:
        raise EnvironmentError(f"Environment variable '{var}' is not set.")
    return value

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
        res = requests.post(url, headers=headers, json=payload, verify=False)
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
        #"model": "llama3.3:70b-instruct-q4_0",
        "model": "llama3.3:70b-instruct-fp16",
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
        reply = json.loads(response.text)["choices"][0]["message"]["content"]
        return int(reply)
    except Exception as e:
        print("Failed to get answer:", e)
        return None

# OCR config presets
OCR_CONFIGS = {
    "question": '--oem 3 --psm 6',
    "option": '--oem 3 --psm 7'
}

def enhance_yellow_region_cv2(image):
    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Detect yellow background
    lower_yellow = np.array([15, 50, 150])
    upper_yellow = np.array([45, 255, 255])
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
    mask_inv = cv2.bitwise_not(mask)

    bg = cv2.bitwise_and(img, img, mask=mask)
    text = cv2.bitwise_and(img, img, mask=mask_inv)

    bg[np.where(mask > 0)] = [255, 255, 255]
    text[np.where(mask_inv > 0)] = [0, 0, 0]

    combined = cv2.add(bg, text)
    gray = cv2.cvtColor(combined, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (0, 0), fx=1.5, fy=1.5, interpolation=cv2.INTER_LINEAR)
    return gray

def preprocess_and_ocr(key, region_pil):
    img = np.array(region_pil.convert('RGB'))

    if key == 3:
        processed = enhance_yellow_region_cv2(region_pil)
        config = OCR_CONFIGS["option"]
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        if key == 0:
            _, processed = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            config = OCR_CONFIGS["question"]
        else:
            # Enhance contrast
            processed = cv2.convertScaleAbs(gray, alpha=2.0, beta=0)
            # Skip unnecessary blur for sharper text
            config = OCR_CONFIGS["option"]

        # Resize only once here for all non-yellow
        processed = cv2.resize(processed, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_LINEAR)

    text = pytesseract.image_to_string(Image.fromarray(processed), config=config)
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
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = pool.map(lambda kv: preprocess_and_ocr(*kv), regions.items())
        for key, text in results:
            if text:
                line = f"Question: {text}" if key == 0 else f"{key}: {text}"
                result_text += line + "\n"

    print(result_text)

    try:
        #print(f"[{datetime.now()}] OCR completed")
        #answer = nims_cloud_answer(result_text)
        answer = ollama_answer(result_text)
        #print(f"[{datetime.now()}] LLM completed")
        click_button(answer if answer in [1, 2, 3, 4] else 1)
        print(f"Predicted answer: {answer}")
        print(f"[{datetime.now()}] click_button completed")
    except Exception as e:
        print("Error in answering/clicking:", e)

keyboard.add_hotkey("ctrl+alt+t", extract_text)

try:
    keyboard.wait()
except KeyboardInterrupt:
    print("Program interrupted and exiting cleanly.")
