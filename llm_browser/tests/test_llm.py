import os

import requests
from dotenv import load_dotenv

from llm_browser.src.llm.models import models

load_dotenv()

data = {
    "model": "llama3.2:3b",
    "prompt": "Why is the sky blue?",
    "stream": False,
}


def test_ollama_endpoint():
    host = os.environ.get("_MONGO_HOST")
    port = os.environ.get("_OLLAMA_PORT")
    url = f"http://{host}:{port}/api/generate"
    response = requests.post(url=url, json=data).json()
    answer: str = response["response"]
    assert answer.__contains__("Rayleigh scattering")


def test_ollama_model():
    model = models.get("ollama")
    messages = [
        ("system", "You are a helpful assistant. Answer the question."),
        ("human", data["prompt"]),
    ]
    msg = model.invoke(messages)
    answer = msg.content
    assert answer.__contains__("Rayleigh scattering")
