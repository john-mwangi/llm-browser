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
from browser_use import Agent, Browser, BrowserConfig
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from playwright._impl._errors import TimeoutError
from playwright.sync_api import sync_playwright

load_dotenv(override=True)

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


async def browse_content(prompt_content, path):
    prompt = prompt_content["prompt"]
    agent = Agent(
        task=prompt,
        llm=models.get(model),
        browser=browser,
        max_input_tokens=max_input_tokens,
    )

    logger.info(f"Using agent: {agent.model_name}")

    try:
        result = await agent.run()
        filename = path.stem
        with open(f"results/{filename}_{ts}.md", mode="w") as f:
            f.write(result.final_result())

    except TimeoutError as e:
        logger.exception(e)


def chunk_string(input_string, max_length):
    chunks = []
    while input_string:
        chunks.append(input_string[:max_length])
        input_string = input_string[max_length:]
    return chunks


def download_content(prompt_content, path):
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
                logger.warning("there was an issue extracting links")
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
                    logger.exception(f"error on '{link.text_content()}': {e}")

                logger.info(f"successfully retrieved '{link.text_content()}' content")

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

        # model_name = models.get(model).model.split("/")[1]
        model_name = "gemini-1.5-flash"

        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
            params=params,
            headers=headers,
            json=json_data,
        )

        logger.info("complete")
        result = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        result = re.sub(r"\n{3,}", "\n\n", result)

        filename = path.stem
        logger.info("posting to channel...")

        # with open(f"results/{title}_{ts}.md", mode="w") as f:
        #     f.write(result)

        heading = f"# Postings for: **{title}**\n\n"
        heading_resp = requests.post(discord_webhook, json={"content": heading.upper()})

        chunks = chunk_string(result, max_length=2000)

        for chunk in chunks:
            json_result = {"content": chunk}
            discord_resp = requests.post(url=discord_webhook, json=json_result)


def main():
    paths = list(Path(__file__).parent.glob("prompts/prompt*.toml"))
    logger.info(f"retrieved {len(paths)} prompts")

    for path in paths:
        with open(path, mode="rb") as f:
            prompt_content = tomllib.load(f)

        task = prompt_content["task"]

        if task == "browse":
            asyncio.run(browse_content(prompt_content, path))
        elif task == "scrape":
            download_content(prompt_content, path)
        else:
            raise ValueError("unknown task")


if "__name__" == "__name__":
    main()
