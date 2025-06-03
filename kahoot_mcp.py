import mss
import pyautogui
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from mcp.server.fastmcp import FastMCP
from concurrent.futures import ThreadPoolExecutor

pytesseract.pytesseract.tesseract_cmd = r"C:\Users\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# Create an MCP server
mcp = FastMCP("Kahoot")

@mcp.tool()
def click_button(button):
    """Click the Kahoot button based on the button number"""
    try:
        button_num = int(button)
        button_coords = {
            1: (0.25, 0.75),
            2: (0.77, 0.75),
            3: (0.25, 0.822),
            4: (0.77, 0.822)
        }
        screen_width, screen_height = pyautogui.size()
        x, y = button_coords[button_num]
        pyautogui.click(int(screen_width * x), int(screen_height * y))
        pyautogui.click(int(screen_width * x), int(screen_height * y))
    except Exception as e:
        raise Exception(f"Button: {button}, Error: {str(e)}")

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

@mcp.tool()
def extract_text():
    """Get the Kahoot question and multiple-choices answer using OCR"""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')

    width, height = img.size
    question_and_answers = {
        0: {"top_left": (0.0, 0.58), "bottom_right": (1.0, 0.73)},
        1: {"top_left": (0.042, 0.725), "bottom_right": (0.458, 0.775)},
        2: {"top_left": (0.542, 0.725), "bottom_right": (1.0, 0.775)},
        3: {"top_left": (0.042, 0.795), "bottom_right": (0.458, 0.85)},
        4: {"top_left": (0.542, 0.795), "bottom_right": (1.0, 0.85)}
    }

    regions = {
        key: img.crop((
            int(width * coords["top_left"][0]),
            int(height * coords["top_left"][1]),
            int(width * coords["bottom_right"][0]),
            int(height * coords["bottom_right"][1])
        ))
        for key, coords in question_and_answers.items()
    }

    result = ""
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(preprocess_and_ocr, key, region) for key, region in regions.items()]
        for future in futures:
            key, text = future.result()
            if text:
                result += f"Question: {text}\n" if key == 0 else f"{key}: {text}\n"
            else:
                print(f"No text detected for region {key}")

    #print(result)
    return result

if __name__ == "__main__":
    mcp.run(transport='stdio')
