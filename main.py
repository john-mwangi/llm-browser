"""Uses an LLM model to autonomously browse the Internet"""

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

models = {
    "openai": ChatOpenAI(model="gpt-4o-mini"),
    "anthropic": ChatAnthropic(model_name="claude-3-5-sonnet-20241022"),
    "ollama": ChatOllama(model="qwen2.5:7b"),
    "gemini": ChatGoogleGenerativeAI(model="gemini-2.0-pro-exp-02-05"),
}


async def main():
    paths = Path(__file__).parent.glob("prompts/prompt*.txt")

    for path in paths:
        with open(path) as f:
            prompt = f.read()

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


def download_content():
    paths = Path(__file__).parent.glob("prompts/prompt*.toml")
    for path in paths:
        with open(path, mode="rb") as f:
            prompt_file = tomllib.load(f)

        url = prompt_file["url"]
        prompt = prompt_file["prompt"]
        title = re.sub("\s+", "_", prompt_file["title"])

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            page.goto(url)
            page.wait_for_selector("body")

            # extract jobs and their descriptions
            roles = page.query_selector_all(selector="div.tNxQIb.PUpOsf")

            data = {}

            for role in roles:
                role.click()
                entity = page.query_selector("div.wHYlTd.MKCbgd.a3jPc").text_content()

                try:
                    page.get_by_role(
                        role="button", name="Show full description"
                    ).click()
                    page.wait_for_load_state("domcontentloaded")
                    content = page.query_selector("div.NgUYpe").text_content()
                    data[role.text_content()] = f"Entity: {entity}\n\n" + content

                except Exception as e:
                    logger.exception(f"error on '{role.text_content()}': {e}")

                logger.info(f"successfully retrieved '{role.text_content()}' content")

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

        model_name = models.get(model).model.split("/")[1]

        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
            params=params,
            headers=headers,
            json=json_data,
        )

        logger.info("complete")
        result = response.json()["candidates"][0]["content"]["parts"][0]["text"]

        filename = path.stem
        with open(f"results/{title}_{ts}.md", mode="w") as f:
            f.write(result)


if "__name__" == "__name__":
    # asyncio.run(main())
    download_content()
