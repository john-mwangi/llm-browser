"""Uses an LLM model to autonomously browse the Internet"""

import asyncio
import logging
import os
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from llm_browser.src.browser.core import browse_content
from llm_browser.src.browser.scrapers import fetch_google, fetch_linkedin
from llm_browser.src.database import get_mongodb_client, save_to_db
from llm_browser.src.llm.models import models
from llm_browser.src.llm.query import filter_query, query_llm
from llm_browser.src.tasks import TaskType
from llm_browser.src.utils import set_logging

load_dotenv(override=True)

set_logging()
logger = logging.getLogger(__name__)

tz = os.environ.get("TZ")
text_model = os.environ.get("TEXT_MODEL")
vision_model = os.environ.get("VISION_MODEL")
webhook = os.environ.get("DISCORD_WEBHOOK")
db_name = os.environ.get("_MONGO_DB")
context_name = os.environ.get("CONTEXT_NAME")


def main():
    client = get_mongodb_client()

    with client:
        db = client[db_name]
        prompts = db["prompts"]
        context = db[context_name]
        resumes = db["resumes"]

        counts_ = context.estimated_document_count()
        logger.info(f"retrieved {counts_} tasks")
        docs = context.find()

        resume_content = resumes.find_one({"type": "data engineer"})["resume"]
        resume_dict = {"resume": resume_content}
        resume_prompt = prompts.find_one({"type": "compare_roles"})["prompt"]
        filter_prompt = prompts.find_one({"type": "filter_roles"})["prompt"]

        for doc in docs:
            run_id = uuid4().hex
            title = doc["title"]
            created_at = datetime.now(tz=ZoneInfo(tz)).strftime(
                "%Y-%m-%d %H%M%S"
            )
            logger.info(f"running task: {title}")

            try:
                task = TaskType(doc["task"])
            except Exception as e:
                raise ValueError(f"unknown task: {task}")

            if task == TaskType.BROWSE:
                main_prompt = prompts.find_one({"type": "browse"})["prompt"]
                url = doc["url"]
                browsing_prompt = main_prompt + "\n\nURL to navigate: " + url

                agent_history = asyncio.run(
                    browse_content(
                        prompt=browsing_prompt,
                        model=models.get(vision_model),
                    )
                )

                final_result = agent_history.final_result()
                alternate_result = agent_history.action_results()[
                    -2
                ].model_dump_json()

                # result_dict = string_to_dict(
                #     texts=[final_result, alternate_result]
                # )

                logger.info(f"browser results: {final_result}")
                result_dict = {"roles": final_result}
                augmented_data = {**result_dict, **resume_dict}

                response = query_llm(
                    data=augmented_data,
                    prompt=resume_prompt,
                    model=models.get(text_model),
                )

                logger.info("saving to database...")
                save_to_db(
                    fp=None,
                    key=None,
                    collection="results",
                    data={
                        "run_id": run_id,
                        "created_at": created_at,
                        "title": title,
                        "result": response,
                    },
                )

                logger.info("saving results to database...")
                save_to_db(
                    fp=None,
                    key=None,
                    collection="results",
                    data={
                        "run_id": run_id,
                        "created_at": created_at,
                        "models": {
                            "vision_model": models.get(vision_model).model,
                            "text_model": models.get(text_model).model,
                        },
                        "title": title,
                        "result": response,
                    },
                )

                logger.info("posting to channel...")
                filter_query(
                    data=response,
                    prompt=filter_prompt,
                    model=models.get(text_model),
                    title=title,
                )

            if task == TaskType.SCRAPE:
                # prompt = prompts.find_one({"type": "google"}, collation={"strength": 2, "locale": "en"})
                # prompt = prompts.find_one(
                #     {"type": {"$regex": "^google$", "$options": "i"}}
                # )["prompt"]

                url: str = doc["url"]

                if url.startswith("https://www.google"):
                    try:
                        data = fetch_google(url)
                    except Exception as e:
                        logger.exception(f"error with {url}: {e}")
                        continue

                if url.startswith("https://www.linkedin"):
                    try:
                        data = fetch_linkedin(url)
                    except Exception as e:
                        logger.exception(f"error with {url}: {e}")
                        continue

                data = {"roles": data} if not isinstance(data, dict) else data

                response = query_llm(
                    data={**data, **resume_dict},
                    prompt=resume_prompt,
                    model=models.get(text_model),
                )

                logger.info("saving results to database...")
                save_to_db(
                    fp=None,
                    key=None,
                    collection="results",
                    data={
                        "run_id": run_id,
                        "created_at": created_at,
                        "models": {
                            "vision_model": models.get(vision_model).model,
                            "text_model": models.get(text_model).model,
                        },
                        "title": title,
                        "result": response,
                    },
                )

                logger.info("posting to channel...")
                filter_query(
                    data=response,
                    prompt=filter_prompt,
                    model=models.get(text_model),
                    title=title,
                )


if "__name__" == "__name__":
    main()
