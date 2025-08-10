import logging
import os
from time import time

import pytest
import requests
from dotenv import load_dotenv

from llm_browser.src.llm.models import models
from llm_browser.src.utils import set_logging

load_dotenv()

set_logging(level=logging.DEBUG)
logger = logging.getLogger(__name__)

host = os.environ.get("_OLLAMA_HOST")
port = os.environ.get("_OLLAMA_PORT")
base_url = f"http://{host}:{port}"
TEST_MODELS = ["llama3.2:3b", "gemma3:4b", "qwen3:4b"]


@pytest.mark.parametrize("model_name", TEST_MODELS)
def test_ollama_endpoint(model_name):
    logger.info(f"Testing Ollama endpoint with model: {model_name}")
    start = time()
    data = {
        "model": model_name,
        "prompt": "Why is the sky blue?",
        "stream": False,
    }
    url = f"{base_url}/api/generate"
    response = requests.post(url=url, json=data).json()
    answer: str = response["response"]
    end = time()
    logger.info(f"LLM answer: {answer}")
    logger.info(f"Response time: {end - start:.2f} seconds")
    assert answer.__contains__("Rayleigh scattering")


def test_ollama_langchain():
    model = models["ollama"]
    model_name = model.model
    logger.info(f"Testing LangChain with Ollama model: {model_name}")
    start = time()
    messages = [
        ("system", "You are a helpful assistant. Answer the question."),
        ("human", "Why is the sky blue?"),
    ]
    msg = model.invoke(messages)
    answer = msg.content
    end = time()
    logger.info(f"{model_name} LLM answer: {answer}")
    logger.info(f"Response time: {end - start:.2f} seconds")
    assert answer.__contains__("Rayleigh scattering")
