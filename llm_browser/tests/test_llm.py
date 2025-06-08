import os

import requests
from dotenv import load_dotenv

load_dotenv()


def test_ollama():
    data = {
        "model": "llama3.2:3b",
        "prompt": "Why is the sky blue?",
        "stream": False,
    }
    host = os.environ.get("_MONGO_HOST")
    port = os.environ.get("_OLLAMA_PORT")
    url = f"http://{host}:{port}/api/generate"
    response = requests.post(url=url, json=data).json()
    answer: str = response["response"]
    assert answer.__contains__("Rayleigh scattering")
