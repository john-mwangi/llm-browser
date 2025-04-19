"""Utility functions for the LLM browser application"""

import json
import logging
import os
import re
from enum import Enum
from pathlib import Path
from urllib.parse import quote_plus

import requests
from browser_use import Agent
from bs4 import BeautifulSoup
from playwright._impl._errors import TimeoutError
from playwright.sync_api import sync_playwright
from pymongo import MongoClient
from requests import Response

ROOT_DIR = Path(__file__).parent.parent
browser_args = [
    "--window-size=1300,570",
    "--window-position=000,000",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-web-security",
    "--disable-features=site-per-process",
    "--disable-setuid-sandbox",
    "--disable-accelerated-2d-canvas",
    "--no-first-run",
    "--no-zygote",
    "--use-gl=egl",
    "--disable-blink-features=AutomationControlled",
    "--disable-background-networking",
    "--enable-features=NetworkService,NetworkServiceInProcess",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-breakpad",
    "--disable-client-side-phishing-detection",
    "--disable-component-extensions-with-background-pages",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-features=Translate",
    "--disable-hang-monitor",
    "--disable-ipc-flooding-protection",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--disable-renderer-backgrounding",
    "--disable-sync",
    "--force-color-profile=srgb",
    "--metrics-recording-only",
    "--enable-automation",
    "--password-store=basic",
    "--use-mock-keychain",
    "--hide-scrollbars",
    "--mute-audio",
    "--ignore-certificate-errors",
    "--enable-webgl",
]


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


async def browse_content(prompt, path, model, browser, max_input_tokens, ts):
    """Browse content using the agent"""
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


def download_content_google(prompt_context: dict, headless: bool):
    """Download and process content from a URL

    Args
    ---
    prompt_content: a record containing the url, title, query, etc.
    headless: boolean indicating whether to use a headless browser
    """
    url = prompt_context["url"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=browser_args)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.75 Safari/537.36",
            locale="en-US",
            permissions=["notifications"],
        )
        # page = context.new_page()
        page = browser.new_page()
        page.goto(url)

        # check for captcha challenge
        captcha = page.locator(
            'iframe[name="a-2bkr1j4vqdhy"]'
        ).content_frame.get_by_role("checkbox", name="I'm not a robot")

        if captcha.is_visible():
            page.pause()

        page.wait_for_selector("body")

        links = page.query_selector_all(selector="div.tNxQIb.PUpOsf")
        entities = page.query_selector_all("div.wHYlTd.MKCbgd.a3jPc")
        entities = [e.text_content().strip() for e in entities]

        if len(links) == 0:
            logging.warning("there was an issue extracting links")

        data = {}

        for link, entity in zip(links, entities):
            link.click()

            try:
                page.get_by_role(role="button", name="Show full description").click()
                page.wait_for_load_state("domcontentloaded")
                content = page.query_selector("div.NgUYpe").text_content()
                data[link.text_content()] = f"Entity: {entity}\n\n" + content

            except Exception as e:
                logging.exception(f"error on '{link.text_content()}': {e}")
                data[link.text_content()] = f"Entity: {entity}\n\n"

            logging.info(f"successfully retrieved '{link.text_content()}' content")

        context.close()
        browser.close()
        return data


def query_google(data: dict, prompt: str, model):
    """Queries an LLM model

    Args
    ---
    data: results of the scraping process
    prompt: the prompt to use
    model: the LangChain model

    Returns
    ---
    An API response
    """

    logging.info("querying llm...")

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

    model_name = model.model.split("/")[-1]

    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
        params=params,
        headers=headers,
        json=json_data,
    )

    return response


def query_llm(data: dict, prompt: str, model) -> str:
    """Queries an LLM model

    Args
    ---
    - data: results of the scraping process
    - prompt: the prompt to use
    - model: the LangChain model

    Returns
    ---
    The LLM response
    """
    logging.info("querying llm...")
    messages = [("system", prompt), ("human", json.dumps(data))]
    msg = model.invoke(messages)
    return msg.content


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

    uri = f"mongodb://{_USER}:{_PASSWORD}@{_HOST}:{_PORT}/"

    return MongoClient(uri), _DB


def format_content(content: str) -> str:
    r1 = re.sub(r"\n{2,}", "\n", content, flags=re.MULTILINE)
    r2 = re.sub(r"^#\s*(.+?)\s*$", r"\n**\1**", r1, flags=re.MULTILINE)
    return r2


def post_response(response: Response | str, webhook: str, title: str):
    """Posts the LLM results to a Discord, WhatApp, Slack, etc. using the webhook

    Args
    ---
    response: the response from the LLM
    webhook: the webhook to post to
    title: the title of the post
    """
    heading = f"# Postings for: **{title.title()}**\n\n"

    if isinstance(response, Response):
        result = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        r2 = format_content(result)
        post = heading + r2

    if isinstance(response, str):
        response = format_content(response)
        post = heading + response

    logging.info("posting to channel...")

    chunks = chunk_string(post, max_length=2000)

    for chunk in chunks:
        json_result = {"content": chunk}
        msg_resp = requests.post(url=webhook, json=json_result)


def extract_transcript(url: str):
    """Extracts the Fireflies transcript

    Args
    ---
    url: of the Fireflies transcript
    """

    meeting_name = url.split("::")[0].split("/")[-1]
    results_dir = ROOT_DIR / "results"
    file_name = f"{meeting_name}.txt"
    file_path = os.path.join(results_dir, file_name)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector(".paragraph-root")
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    paragraphs = soup.find_all("div", class_="paragraph-root")

    markdown_output = []

    for para in paragraphs:
        # Extract name
        name_span = para.find("span", class_="name")
        name = name_span.text.strip() if name_span else "Unknown"

        # Extract timestamp
        timestamp_span = para.find("span", class_="sc-871c1b8d-0")
        timestamp = timestamp_span.text.strip() if timestamp_span else "00:00"

        # Extract message
        message_div = para.find("div", class_="transcript-sentence")
        message = message_div.text.strip() if message_div else ""

        # Format the line
        markdown_line = f"{name} - {timestamp}\n{message}\n"
        markdown_output.append(markdown_line)

    with open(file_path, "w") as f:
        f.writelines(markdown_output)
