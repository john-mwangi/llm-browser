"""Utility functions for the LLM browser application"""

import logging
import os
import re
from enum import Enum
from urllib.parse import quote_plus

import requests
from browser_use import Agent
from playwright._impl._errors import TimeoutError
from playwright.sync_api import sync_playwright
from pymongo import MongoClient
from requests import Response


class TaskType(Enum):
    """Enum representing different types of tasks that can be performed"""

    BROWSE = "browse"
    SCRAPE = "scrape"


def set_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True
    )


def chunk_string(input_string, max_length):
    """Split a string into chunks of specified maximum length"""
    chunks = []
    while input_string:
        chunks.append(input_string[:max_length])
        input_string = input_string[max_length:]
    return chunks


async def browse_content(prompt_content, path, model, browser, max_input_tokens, ts):
    """Browse content using the agent"""
    prompt = prompt_content["prompt"]
    agent = Agent(
        task=prompt,
        llm=model,
        browser=browser,
        max_input_tokens=max_input_tokens,
    )

    logging.info(f"Using agent: {agent.model_name}")

    try:
        result = await agent.run()
        filename = path.stem
        with open(f"results/{filename}_{ts}.md", mode="w") as f:
            f.write(result.final_result())

    except TimeoutError as e:
        logging.exception(e)


def download_content(prompt_content, headless):
    """Download and process content from a URL"""
    url = prompt_content["url"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(url)

        if url.startswith("https://www.google"):
            page.wait_for_selector("body")

            links = page.query_selector_all(selector="div.tNxQIb.PUpOsf")
            entities = page.query_selector_all("div.wHYlTd.MKCbgd.a3jPc")
            entities = [e.text_content().strip() for e in entities]

            if len(links) == 0:
                logging.warning("there was an issue extracting links")
                return

            data = {}

            for link, entity in zip(links, entities):
                link.click()

                try:
                    page.get_by_role(
                        role="button", name="Show full description"
                    ).click()
                    page.wait_for_load_state("domcontentloaded")
                    content = page.query_selector("div.NgUYpe").text_content()
                    data[link.text_content()] = f"Entity: {entity}\n\n" + content

                except Exception as e:
                    logging.exception(f"error on '{link.text_content()}': {e}")
                    data[link.text_content()] = f"Entity: {entity}\n\n"

                logging.info(f"successfully retrieved '{link.text_content()}' content")

        browser.close()
        return data


def query_llm(data: dict, prompt: str):
    """Queries an LLM model

    Args
    ---
    data: results of the scraping process

    Returns
    ---
    An API response
    """

    headers = {"Content-Type": "application/json"}
    params = {"key": os.getenv("GOOGLE_API_KEY", "")}
    prompt += f"\ndata: {data}"

    json_data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    },
                ],
            },
        ],
    }

    model_name = "gemini-1.5-flash"

    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
        params=params,
        headers=headers,
        json=json_data,
    )

    logging.info("llm querying complete")

    return response


def get_mongodb_client():
    """Establishes a MongoDB client

    Returns
    ---
    Tuple of (MongoClient, database_name)
    """

    _USER = os.environ.get("_MONGO_UNAME")
    _PASSWORD = quote_plus(os.environ.get("_MONGO_PWD"))
    _HOST = os.environ.get("_MONGO_HOST")
    _DB = os.environ.get("_MONGO_DB")
    _PORT = os.environ.get("_MONGO_PORT")

    uri = f"mongodb://{_USER}:{_PASSWORD}@{_HOST}:{_PORT}/?authSource={_DB}"

    return MongoClient(uri), _DB


def post_response(response: Response, webhook: str, title: str):
    """Posts the LLM results to a Discord, WhatApp, Slack, etc. using the webhook

    Args
    ---
    response: the response from the LLM
    webhook: the webhook to post to
    title: the title of the post
    """
    heading = f"# Postings for: **{title}**\n\n"
    result = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    r1 = re.sub(r"\n{2,}", "\n", result, flags=re.MULTILINE)
    r2 = re.sub(r"^#\s*(.+?)\s*$", r"\n**\1**", r1, flags=re.MULTILINE)
    r3 = heading + r2

    logging.info("posting to channel...")

    chunks = chunk_string(r3, max_length=2000)

    for chunk in chunks:
        json_result = {"content": chunk}
        discord_resp = requests.post(url=webhook, json=json_result)
