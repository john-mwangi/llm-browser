"""Playwright setup, basic browser context/page creation, Agent class from browser_use"""


async def browse_content(prompt, model, browser, max_input_tokens):
    """Browse content using the agent"""
    agent = Agent(
        task=prompt,
        llm=model,
        browser=browser,
        max_input_tokens=max_input_tokens,
    )

    logging.info(f"Using agent: {agent.model_name}")

    result = await agent.run()
    return result
