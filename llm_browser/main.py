"""Uses an LLM model to autonomously browse the Internet"""

import asyncio
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from llm_browser.src.browser.core import browse_content
from llm_browser.src.browser.scrapers import download_content_google
from llm_browser.src.database import get_mongodb_client
from llm_browser.src.llm.models import models
from llm_browser.src.llm.query import query_llm
from llm_browser.src.reporting import post_response
from llm_browser.src.tasks import TaskType
from llm_browser.src.utils import set_logging

load_dotenv(override=True)

set_logging()
logger = logging.getLogger(__name__)

tz = os.environ.get("TZ")
text_model = os.environ.get("TEXT_MODEL")
vision_model = os.environ.get("VISION_MODEL")
ts = datetime.now(tz=ZoneInfo(tz)).strftime("%Y-%m-%d_%H%M%S")
webhook = os.environ.get("DISCORD_WEBHOOK")
db_name = os.environ.get("_MONGO_DB")


def main():
    client = get_mongodb_client()

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
            resume_content = resumes.find_one({"type": "data engineer"})[
                "resume"
            ]
            resume = {"resume": resume_content}
            resume_prompt = prompts.find_one({"type": "google_augmented"})[
                "prompt"
            ]

            if task == TaskType.BROWSE:
                main_prompt = prompts.find_one({"type": "browse"})["prompt"]
                url = doc["url"]
                browsing_prompt = main_prompt + "\n\nURL to navigate: " + url

                result = asyncio.run(
                    browse_content(
                        prompt=browsing_prompt,
                        model=models.get(vision_model),
                    )
                )

                augmented_data = {**result, **resume}

                response = query_llm(
                    data=augmented_data,
                    prompt=resume_prompt,
                    model=models.get(text_model),
                )

                post_response(response=response, webhook=webhook, title=title)

            if task == TaskType.SCRAPE:
                # prompt = prompts.find_one({"type": "google"}, collation={"strength": 2, "locale": "en"})
                # prompt = prompts.find_one(
                #     {"type": {"$regex": "^google$", "$options": "i"}}
                # )["prompt"]

                data = download_content_google(prompt_context=dict(doc))

                response = query_llm(
                    data={**data, **resume},
                    prompt=resume_prompt,
                    model=models.get(text_model),
                )
                post_response(response=response, webhook=webhook, title=title)


if "__name__" == "__name__":
    main()
