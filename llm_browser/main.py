"""Uses an LLM model to autonomously browse the Internet"""

import asyncio
import json
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from browser_use import Browser, BrowserConfig
from dotenv import load_dotenv
from src import utils
from src.utils import TaskType, models, set_logging

load_dotenv(override=True)

set_logging()
logger = logging.getLogger(__name__)

tz = os.environ.get("TZ")
text_model = os.environ.get("TEXT_MODEL")
vision_model = os.environ.get("VISION_MODEL")
max_input_tokens = int(os.environ.get("MAX_INPUT_TOKENS", 120000))
headless = bool(int(os.environ.get("HEADLESS"), 0))
browser = Browser(config=BrowserConfig(headless=headless))
ts = datetime.now(tz=ZoneInfo(tz)).strftime("%Y-%m-%d_%H%M%S")
webhook = os.environ.get("DISCORD_WEBHOOK")


def main():
    client, db_name = utils.get_mongodb_client()

    with client:
        db = client[db_name]
        prompts = db["prompts"]
        context = db["context"]
        resumes = db["resumes"]

        counts_ = context.estimated_document_count()
        logger.info(f"retrieved {counts_} tasks")
        docs = context.find()

        for doc in docs:
            try:
                task = TaskType(doc["task"])
            except Exception as e:
                raise ValueError(f"unknown task: {task}")

            title = doc["title"]
            resume_content = resumes.find_one({"type": "data engineer"})["resume"]
            resume = {"resume": resume_content}
            resume_prompt = prompts.find_one({"type": "google_augmented"})["prompt"]

            if task == TaskType.BROWSE:
                main_prompt = prompts.find_one({"type": "browse"})["prompt"]
                url = doc["url"]
                browsing_prompt = main_prompt + "\n\nURL to navigate: " + url

                result = asyncio.run(
                    utils.browse_content(
                        prompt=browsing_prompt,
                        model=models.get(vision_model),
                        browser=browser,
                        max_input_tokens=max_input_tokens,
                    )
                )

                augmented_data = {**result, **resume}

                response = utils.query_llm(
                    data=augmented_data,
                    prompt=resume_prompt,
                    model=models.get(text_model),
                )

                utils.post_response(response=response, webhook=webhook, title=title)

            if task == TaskType.SCRAPE:
                # prompt = prompts.find_one({"type": "google"}, collation={"strength": 2, "locale": "en"})
                # prompt = prompts.find_one(
                #     {"type": {"$regex": "^google$", "$options": "i"}}
                # )["prompt"]

                data = utils.download_content_google(
                    prompt_context=dict(doc), headless=headless
                )
                response = utils.query_llm(
                    data={**data, **resume},
                    prompt=resume_prompt,
                    model=models.get(text_model),
                )
                utils.post_response(response=response, webhook=webhook, title=title)


if "__name__" == "__name__":
    main()
