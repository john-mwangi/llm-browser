"""Uses an LLM model to autonomously browse the Internet"""

import asyncio
import json
import logging
import os
from datetime import datetime
from time import sleep
from uuid import uuid4
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from playwright.async_api import BrowserContext, async_playwright
from playwright.sync_api import BrowserContext as SBrowserContext
from playwright.sync_api import sync_playwright

from llm_browser.src.browser.core import browse_content
from llm_browser.src.browser.scrapers import fetch_google, fetch_linkedin
from llm_browser.src.configs.config import RateLimit, browser_args
from llm_browser.src.database import get_mongodb_client, save_to_db
from llm_browser.src.llm.models import models
from llm_browser.src.llm.query import filter_query, query_llm
from llm_browser.src.tasks import TaskType
from llm_browser.src.utils import set_logging

load_dotenv(override=True)

set_logging()
logger = logging.getLogger(__name__)

tz = os.environ.get("TZ", "UTC")
text_model = os.environ.get("TEXT_MODEL")
vision_model = os.environ.get("VISION_MODEL")
db_name = os.environ.get("_MONGO_DB")
context_name = os.environ.get("CONTEXT_NAME")
rate_limit = RateLimit()


def get_information() -> dict:
    """Retrieves information from the database including urls, prompts, tasks,
    etc.

    Returns
    ---
    - A dictionary with database contents
    """

    client = get_mongodb_client()

    with client:
        db = client[db_name]
        prompts = db["prompts"]
        context = db[context_name]
        resumes = db["resumes"]

        counts_ = context.estimated_document_count()
        logger.info(f"retrieved {counts_} tasks")
        docs = context.find()

        resume = resumes.find_one({"type": "data engineer"})["resume"]
        resume_prompt = prompts.find_one({"type": "compare_roles"})["prompt"]
        filter_prompt = prompts.find_one({"type": "filter_roles"})["prompt"]
        main_prompt = prompts.find_one({"type": "browse"})["prompt"]

        sync_urls: list[tuple] = []
        async_urls: list[tuple] = []

        criteria = ["https://www.linkedin"]

        for c in criteria:
            for doc in docs:
                if doc["url"].startswith(c):
                    sync_urls.append((doc["url"], doc["title"], doc["task"]))
                else:
                    async_urls.append((doc["url"], doc["title"], doc["task"]))

    return {
        "sync_urls": sync_urls,
        "async_urls": async_urls,
        "resume": resume,
        "resume_prompt": resume_prompt,
        "filter_prompt": filter_prompt,
        "main_prompt": main_prompt,
    }


def run_sync(
    url_content: tuple,
    browser_context: SBrowserContext,
    roles_limit: int = None,
) -> list[dict]:
    """Given a url, runs the synchronous instance of the browser on the
    urls.

    Args
    ---
    - content: a list of urls to access synchronously as well as their titles and task names.
    - browser_context: a synchronous instance of the Playwright browser

    Returns
    ---
    - Data scraped from a url
    """

    result = []
    url, title, _ = url_content
    run_id = uuid4().hex
    created_at = datetime.now(tz=ZoneInfo(tz)).strftime("%Y-%m-%d %H%M%S")
    if url.startswith("https://www.linkedin"):
        try:
            roles = fetch_linkedin(url, browser_context, limit=roles_limit)
            result.append(
                {
                    "roles": roles,
                    "title": title,
                    "run_id": run_id,
                    "created_at": created_at,
                }
            )
            logger.info(f"retrieved {len(roles)} roles from {url}")
        except Exception as e:
            logger.exception(f"error with {url}: {e}")

    return result


async def run_async(
    url_content: tuple,
    browser_context: BrowserContext,
    main_prompt: str,
    roles_limit: int = None,
) -> list[dict]:
    """Given a list of urls, runs an ansynchronous instance of the browser on the
    urls.

    Args
    ---
    - content: a list of urls to browse asynchronously as well as their titles
    and task names.
    - browser_context: an asynchronous instance of a Playwright browser.

    Returns
    ---
    - Data scraped from a url
    """

    result = []
    url, title, task = url_content
    run_id = uuid4().hex
    created_at = datetime.now(tz=ZoneInfo(tz)).strftime("%Y-%m-%d %H%M%S")

    try:
        task_type = TaskType(task.strip().lower())
    except Exception:
        logger.exception(f"unknown task: {task}")

    if task_type == TaskType.BROWSE:
        browsing_prompt = main_prompt + "\n\nURL to navigate: " + url

        agent_history = await browse_content(
            prompt=browsing_prompt,
            model=models.get(vision_model),
        )

        final_result = agent_history.final_result()
        alternate_result = agent_history.action_results()[-2].model_dump_json()

        roles = json.loads(final_result)
        result.append(
            {
                "roles": roles,
                "title": title,
                "run_id": run_id,
                "created_at": created_at,
            }
        )

    if task_type == TaskType.SCRAPE:
        if url.startswith("https://www.google"):
            try:
                roles = await fetch_google(
                    url, context=browser_context, limit=roles_limit
                )
                result.append(
                    {
                        "roles": roles,
                        "title": title,
                        "run_id": run_id,
                        "created_at": created_at,
                    }
                )
                logger.info(f"retrieved {len(roles)} roles from {url}")
            except Exception as e:
                logger.exception(f"error with {url}: {e}")

    return result


def process_results(results: list[dict], prompts: dict) -> None:
    """Interacts with an LLM models to process the provided results.

    Args
    ---
    - results: the content to be analysed by the LLM
    - prompts: the prompt to guide the LLM

    Returns
    ---
    LLM response in markdown format is posted to a channel or save to the db
    """
    resume = prompts["resume"]
    filter_prompt = prompts["filter_prompt"]
    resume_prompt = prompts["resume_prompt"]

    delay = (1 / rate_limit.gemini_2_0) + rate_limit.min_delay

    for result in results:
        roles = result["roles"]
        response = query_llm(
            data={**{"roles": roles}, **{"resume": resume}},
            prompt=resume_prompt,
            model=models.get(text_model),
        )

        logger.info("saving results to database...")
        save_to_db(
            fp=None,
            key=None,
            collection="results",
            data={
                "run_id": result["run_id"],
                "created_at": result["created_at"],
                "models": {
                    "vision_model": models.get(vision_model).model,
                    "text_model": models.get(text_model).model,
                },
                "title": result["title"],
                "result": response,
            },
        )

        logger.info("posting to channel...")
        filter_query(
            data=response,
            prompt=filter_prompt,
            model=models.get(text_model),
            title=result["title"],
        )

        sleep(delay)


def main(urls_limit: int | None = None, roles_limit: int = None) -> None:
    # retrieve the necessary information
    content = get_information()

    # retrieve the urls to browse
    if urls_limit is not None:
        logger.info(f"Retrieving only {urls_limit} urls")
        sync_urls = content["sync_urls"][:urls_limit]
        async_urls = content["async_urls"][:urls_limit]
    else:
        sync_urls = content["sync_urls"]
        async_urls = content["async_urls"]

    # run sync browser
    for url in sync_urls:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=browser_args)
            context = browser.new_context()
            results_sync = run_sync(
                url_content=url,
                browser_context=context,
                roles_limit=roles_limit,
            )

        # process sync results with llm
        process_results(results=results_sync, prompts=content)

    # run async browser
    async def run(url_content: tuple) -> list[dict]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False, args=browser_args
            )
            context = await browser.new_context()
            results = await run_async(
                main_prompt=content["main_prompt"],
                browser_context=context,
                url_content=url_content,
                roles_limit=roles_limit,
            )
        return results

    for url in async_urls:
        results_async = asyncio.run(run(url_content=url))

        # process async results with llm
        process_results(results=results_async, prompts=content)

    logger.info("~~~ TASK COMPLETED!!! ~~~")


if __name__ == "__main__":
    main()
