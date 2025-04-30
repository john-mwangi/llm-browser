"""Functions for querying LLMs"""

import json
import logging

from llm_browser.src.utils import set_logging

set_logging()
logger = logging.getLogger(__name__)


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
