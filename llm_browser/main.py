"""Uses an LLM model to autonomously browse the Internet"""

import asyncio
import logging
import os
import re
import tomllib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from browser_use import Browser, BrowserConfig
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from playwright._impl._errors import TimeoutError
from playwright.sync_api import sync_playwright

from src.utils import set_logging, browse_content, download_content, TaskType

load_dotenv(override=True)

set_logging()
logger = logging.getLogger(__name__)

tz = os.environ.get("TZ")
model = os.environ.get("MODEL")
max_input_tokens = int(os.environ.get("MAX_INPUT_TOKENS", 120000))
headless = bool(int(os.environ.get("HEADLESS"), 0))
browser = Browser(config=BrowserConfig(headless=headless))
ts = datetime.now(tz=ZoneInfo(tz)).strftime("%Y-%m-%d_%H%M%S")
discord_webhook = os.environ.get("DISCORD_WEBHOOK")

models = {
    "openai": ChatOpenAI(model="gpt-4o-mini"),
    "anthropic": ChatAnthropic(model_name="claude-3-5-sonnet-20241022"),
    "ollama": ChatOllama(model="qwen2.5:7b"),
    "gemini": ChatGoogleGenerativeAI(model="gemini-2.0-pro-exp-02-05"),
}


def main():
    paths = list(Path(__file__).parent.glob("prompts/prompt*.toml"))
    logger.info(f"retrieved {len(paths)} prompts")

    for path in paths:
        with open(path, mode="rb") as f:
            prompt_content = tomllib.load(f)

        task = TaskType(prompt_content["task"])

        if task == TaskType.BROWSE:
            asyncio.run(browse_content(prompt_content, path, models.get(model), browser, max_input_tokens, ts))
        elif task == TaskType.SCRAPE:
            download_content(prompt_content, path, headless, discord_webhook, ts)
        else:
            raise ValueError(f"unknown task: {task}")


if "__name__" == "__name__":
    main()
