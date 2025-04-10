"""Uses an LLM model to autonomously browse the Internet"""

import asyncio
import logging
import os
import tomllib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from browser_use import Browser, BrowserConfig
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from src import utils
from src.utils import TaskType, set_logging

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

        try:
            task = TaskType(prompt_content["task"])
        except Exception as e:
            raise ValueError(f"unknown task: {task}")

        title = prompt_content["title"]
        prompt = prompt_content["prompt"]

        if task == TaskType.BROWSE:
            asyncio.run(
                utils.browse_content(
                    prompt_content,
                    path,
                    models.get(model),
                    browser,
                    max_input_tokens,
                    ts,
                )
            )

        if task == TaskType.SCRAPE:
            data = utils.download_content(prompt_content, headless)
            response = utils.query_llm(data=data, prompt=prompt)
            utils.post_response(response=response, webhook=discord_webhook, title=title)


if "__name__" == "__name__":
    main()
