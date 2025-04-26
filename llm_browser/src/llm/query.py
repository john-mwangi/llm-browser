"""Functions for querying LLMs"""

import json

from llm_browser.src.utils import set_logging

logger = set_logging()


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
    logger.info("querying llm...")
    messages = [("system", prompt), ("human", json.dumps(data))]
    msg = model.invoke(messages)
    return msg.content
