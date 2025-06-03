# Kahoot MCP Server

This is a script that automatically screenshots Kahoot game questions and options, processes them using OCR, and consults an LLM to predict the most likely correct answer. It can also act as an MCP server to work with Claude Desktop and other agents.

---

## Prerequisites

* Python 3.8 or above
* Tesseract OCR installed and accessible via environment variable
* MCP-compatible client (e.g. Claude Desktop)

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/....
cd kahoot-mcp-server
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Tesseract OCR

* Download and install from [here](https://github.com/tesseract-ocr/tessdoc).
* Note the installation path (e.g. `C:\Program Files\Tesseract-OCR\tesseract.exe`).

---

## Environment Configuration

To avoid hardcoding sensitive or system-specific values:

1. Create a `.env` file in the project root:

```
TESSERACT_PATH=C:\Path\To\tesseract.exe
NVIDIA_API_KEY=your_nvidia_api_key (optional)
NVIDIA_API_URL=https://integrate.api.nvidia.com/v1/chat/completions (optional)
OLLAMA_API_URL=http://localhost:11434/v1/chat/completions
```

2. These will be automatically loaded by the script at runtime.

---

## Using `kahoot_live.py`

This script lets you manually trigger a screenshot + answer prediction with a hotkey.

### Steps:

1. Launch your Kahoot game and ensure it’s visible on your screen.
2. Run the script:

```bash
python kahoot_live.py
```

3. Press `Ctrl + Alt + t` to capture the question and get the predicted answer.
4. To exit, press `Ctrl + c`.

---

## Running the MCP Server

This lets you connect the bot to Claude Desktop (or other agents using the MCP protocol).

### Adding MCP Server to Claude Desktop:

1. Open Claude Desktop.
2. Go to **File → Settings → Developer**.
3. Click **"Edit Config"**.
4. Open **claude_desktop_config.json** & add path to **kahoot_mcp.py**
```
{
    "mcpServers": {
        "kahoot": {
            "command": "python",
            "args": [
                "C:\\Users\\kahoot_mcp.py"
            ]
        }
    }
}
```
5. Claude will now be able to interact with the Kahoot MCP Server directly.

---

## Notes

* The script assumes a 1440p screen resolution. You may need to tweak the coordinates if you're using a different resolution or layout.
* The bot predicts based on text. It may be inaccurate for image or video questions.
* The coordinates used are percentage-based, so it may adapt well across similar screen sizes.
