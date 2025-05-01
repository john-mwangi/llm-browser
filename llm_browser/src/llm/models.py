"""Definition and initialization of LangChain models (ChatOpenAI, ChatGoogleGenerativeAI, etc.)"""

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

models = {
    "openai": ChatOpenAI(model="gpt-4o-mini"),
    "anthropic": ChatAnthropic(model_name="claude-3-5-sonnet-20241022"),
    "ollama": ChatOllama(model="llama3.2:latest"),
    "gemini-vision": ChatGoogleGenerativeAI(model="gemini-2.0-flash"),
    "gemini-text": ChatGoogleGenerativeAI(model="gemini-1.5-flash"),
}
