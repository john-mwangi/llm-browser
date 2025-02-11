# LLM Browser
## About
Browses the Internet autonomously using an LLM model. Reads the prompt from a text file and saves the result in a markdown file at the root.

## Features
1. Allows you to save a list of frequently used prompts.
2. Works with Ollama to bypass commmercial API rate limits.
3. Sends an email of the results or alternatively, saves them locally.

## Usage
1. Create a python v3.11 virtual environment and install the requirements.
```
pip install -r requirements.txt
```
2. Add a `prompt.txt` file at the root with the prompt you want the model to generate content for.
3. Create a `.env` file at the root with in the following format:
```
GOOGLE_API_KEY=XXX
TZ=Africa/Nairobi
MODEL=gemini
MAX_INPUT_TOKENS=120000
HEADLESS=1
```
4. Run `main.py`

## Demo
In the video below, the model was tasked with adding grocery items to cart, and checking out.

[![AI Did My Groceries](https://github.com/user-attachments/assets/d9359085-bde6-41d4-aa4e-6520d0221872)](https://www.youtube.com/watch?v=L2Ya9PYNns8)
