"""Playwright setup, basic browser context/page creation, Agent class from browser_use"""

import logging
import os

from browser_use import Agent, Browser, BrowserConfig
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from llm_browser.src.configs.config import browser_args
from llm_browser.src.utils import set_logging

load_dotenv()

set_logging()
logger = logging.getLogger(__name__)

headless = bool(int(os.environ.get("HEADLESS"), 0))
browser = Browser(config=BrowserConfig(headless=headless))
max_input_tokens = int(os.environ.get("MAX_INPUT_TOKENS", 120000))


async def browse_content(
    prompt, model, browser=browser, max_input_tokens=max_input_tokens
):
    """Browse content using the agent"""
    agent = Agent(
        task=prompt,
        llm=model,
        browser=browser,
        max_input_tokens=max_input_tokens,
    )

    logger.info(f"Using agent: {agent.model_name}")
    result = await agent.run()
    return result


def setup_playwright_browser(headless: bool = False):
    """Create a browser instance"""

    p = sync_playwright().start()
    browser = p.chromium.launch(headless=headless, args=browser_args)

    return browser, p
