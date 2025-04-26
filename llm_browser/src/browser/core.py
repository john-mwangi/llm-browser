"""Playwright setup, basic browser context/page creation, Agent class from browser_use"""

from browser_use import Agent

from llm_browser.src.utils import set_logging

logger = set_logging()


async def browse_content(prompt, model, browser, max_input_tokens):
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


# TODO: Set up browser
