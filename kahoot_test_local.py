import keyboard
import pyautogui
import pytesseract
import requests
import json
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter

pytesseract.pytesseract.tesseract_cmd = r"C:\Users\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"  # Path to tesseract.exe example path: r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def click_button(button):
    # Percentage-based coordinates for each button
    #button_coords = {1: (0.25, 0.78), 2: (0.77, 0.78), 3: (0.25, 0.85), 4: (0.77, 0.85)}
    ## No External Monitor Coordinates
    button_coords = {1: (0.25, 0.75), 2: (0.77, 0.75), 3: (0.25, 0.822), 4: (0.77, 0.822)}
    screen_width, screen_height = pyautogui.size()
    x, y = button_coords[button]
    x = int(screen_width * x)
    y = int(screen_height * y)
    pyautogui.click(x, y)

def ollama_answer(question_and_answers):
    url = "http://ollama.com/v1/chat/completions"
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
        #print(response.text)  # Print the response for debugging

        # Extract the assistant's reply
        data = json.loads(response.text)
        reply = data["choices"][0]["message"]["content"]
        #print(f"Reply: {reply}")

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

def extract_text():
    print("extract_text Working" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n" )
    # Capture a full-screen screenshot
    img = pyautogui.screenshot()

    # Percentage-based coordinates for kahoot question and answers
    # question_and_answers = {
    #     0: {"top_left": (0.0, 0.58), "bottom_right": (1.0, 0.73)},
    #     1: {"top_left": (0.042, 0.75), "bottom_right": (0.458, 0.8)},
    #     2: {"top_left": (0.542, 0.75), "bottom_right": (1.0, 0.8)},
    #     3: {"top_left": (0.042, 0.82), "bottom_right": (0.458, 0.875)},
    #     4: {"top_left": (0.542, 0.82), "bottom_right": (1.0, 0.875)},
    # }
    ## No External Monitor Coordinates
    question_and_answers = {
        0: {"top_left": (0.0, 0.58), "bottom_right": (1.0, 0.73)},
        1: {"top_left": (0.042, 0.725), "bottom_right": (0.458, 0.775)},
        2: {"top_left": (0.542, 0.725), "bottom_right": (1.0, 0.775)},
        3: {"top_left": (0.042, 0.795), "bottom_right": (0.458, 0.85)},
        4: {"top_left": (0.542, 0.795), "bottom_right": (1.0, 0.85)},
    }

    # Load the image
    width, height = img.size

    res = ""
    for key, coords in question_and_answers.items():
        x1 = int(width * coords["top_left"][0])
        y1 = int(height * coords["top_left"][1])
        x2 = int(width * coords["bottom_right"][0])
        y2 = int(height * coords["bottom_right"][1])
        region = img.crop((x1, y1, x2, y2))

        # For the question (black text on white), use binarization
        if key == 0:
            region = region.convert('L')
            # Apply a binary threshold
            threshold = 180
            region = region.point(lambda p: 255 if p > threshold else 0)
            #region.save(f"debug_region_{key}.png")
            region = region.resize((region.width * 2, region.height * 2))
            custom_config = r'--oem 3 --psm 6'
        else:
            # For answers, use grayscale + strong contrast + sharpen
            region = region.convert('L')
            enhancer = ImageEnhance.Contrast(region)
            region = enhancer.enhance(3.0)
            region = region.filter(ImageFilter.SHARPEN)
            #region.save(f"debug_region_{key}.png")
            region = region.resize((region.width * 2, region.height * 2))
            custom_config = r'--oem 3 --psm 7'

        screenshot_text = pytesseract.image_to_string(region, config=custom_config)

        if not screenshot_text.strip():
            print("No text detected.")
            continue

        if key == 0:
            res += f"Question: {screenshot_text}"
        else:
            res += f"{key}: {screenshot_text}"
    print(res)
    try:
        answer = ollama_answer(res)
        print("extract_text Done" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n" )
        click_button(answer)
        #click_button(4)  # For testing, always click button 1
        print(f"Answer: {answer}")
    except:
        print("answer failed")

# Bind the function to a hotkey
keyboard.add_hotkey("ctrl+alt+t", extract_text)
# Keep the program running
keyboard.wait()

#if __name__ == "__main__":
#    ollama_answer("QUESTION: 1+1 1: 2 2: 3 3: 4 4: 5")
