"""Definition and initialization of LangChain models (ChatOpenAI, ChatGoogleGenerativeAI, etc.)"""

import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

load_dotenv()

host = os.environ.get("_MONGO_HOST")
port = os.environ.get("_OLLAMA_PORT")
base_url = f"http://{host}:{port}"

models = {
    "openai": ChatOpenAI(model="gpt-4o-mini"),
    "anthropic": ChatAnthropic(model_name="claude-3-5-sonnet-20241022"),
    "ollama": ChatOllama(
        model="llama3.2:3b", base_url=base_url, disable_streaming=True
    ),
    "gemini-vision": ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite"),
    "gemini-text": ChatGoogleGenerativeAI(model="gemini-2.0-flash"),
}
