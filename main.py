"""Uses an LLM model to autonomously browse the Internet"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from browser_use import Agent, Browser, BrowserConfig
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

load_dotenv()

logger = logging.getLogger(__name__)

tz = os.environ.get("TZ")
model = os.environ.get("MODEL")
max_input_tokens = int(os.environ.get("MAX_INPUT_TOKENS", 120000))
headless = bool(int(os.environ.get("HEADLESS")))
browser = Browser(config=BrowserConfig(headless=headless))
ts = datetime.now(tz=ZoneInfo(tz)).strftime("%Y-%m-%d_%H%M%S")

models = {
    "openai": ChatOpenAI(model="gpt-4o-mini"),
    "anthropic": ChatAnthropic(model_name="claude-3-5-sonnet-20241022"),
    "ollama": ChatOllama(model="qwen2.5:7b"),
    "gemini": ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp"),
}


async def main():
    paths = Path(__file__).parent.glob("prompt*.txt")

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
            with open(f"{filename}_{ts}.md", mode="w") as f:
                f.write(result.final_result())

        except Exception as e:
            logger.exception(e)


if "__name__" == "__name__":
    asyncio.run(main())
