"""Utility functions for the LLM browser application"""

import asyncio
import logging
import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from browser_use import Agent, Browser
from playwright._impl._errors import TimeoutError
from playwright.sync_api import sync_playwright


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


def download_content(prompt_content, path, headless, discord_webhook, ts):
    """Download and process content from a URL"""
    url = prompt_content["url"]
    prompt = prompt_content["prompt"]
    title = re.sub("\s+", "_", prompt_content["title"])

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(url)

        if url.startswith("https://www.google"):
            page.wait_for_selector("body")

            links = page.query_selector_all(selector="div.tNxQIb.PUpOsf")
            entities = page.query_selector_all("div.wHYlTd.MKCbgd.a3jPc")
            entities = [e.text_content() for e in entities]

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

                logging.info(f"successfully retrieved '{link.text_content()}' content")

        browser.close()

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

        logging.info("complete")
        result = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        result = re.sub(r"\n{3,}", "\n\n", result)

        filename = path.stem
        logging.info("posting to channel...")

        heading = f"# Postings for: **{title}**\n\n"
        heading_resp = requests.post(discord_webhook, json={"content": heading.upper()})

        chunks = chunk_string(result, max_length=2000)

        for chunk in chunks:
            json_result = {"content": chunk}
            discord_resp = requests.post(url=discord_webhook, json=json_result) 