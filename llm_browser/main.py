"""Uses an LLM model to autonomously browse the Internet"""

import asyncio
import logging
import os
from datetime import datetime
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
    "ollama": ChatOllama(model="llama3.2:latest"),
    # "gemini": ChatGoogleGenerativeAI(model="gemini-2.0-pro-exp-02-05"),
    "gemini": ChatGoogleGenerativeAI(model="gemini-1.5-flash"),
}


def main():
    client, db_name = utils.get_mongodb_client()

    with client:
        db = client[db_name]
        prompts = db.prompts
        counts_ = prompts.estimated_document_count()
        logger.info(f"retrieved {counts_} prompts")
        docs = prompts.find()

        for doc in docs:
            try:
                task = TaskType(doc["task"])
            except Exception as e:
                raise ValueError(f"unknown task: {task}")

            title = doc["title"]
            prompt = doc["prompt"]

            if task == TaskType.BROWSE:
                asyncio.run(
                    utils.browse_content(
                        prompt_content=dict(doc),
                        path=None,
                        model=models.get(model),
                        browser=browser,
                        max_input_tokens=max_input_tokens,
                        ts=ts,
                    )
                )

            if task == TaskType.SCRAPE:
                data = utils.download_content(
                    prompt_content=dict(doc), headless=headless
                )
                response = utils.query_llm(
                    data=data, prompt=prompt, model=models.get(model)
                )
                utils.post_response(
                    response=response, webhook=discord_webhook, title=title
                )


if "__name__" == "__name__":
    main()
