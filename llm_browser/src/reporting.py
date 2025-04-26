"""Functions for sending results, formating content, etc"""

import re

import requests
from requests import Response

from llm_browser.src.utils import chunk_string, set_logging

logger = set_logging()


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
        result = response.json()["candidates"][0]["content"]["parts"][0][
            "text"
        ]
        r2 = format_content(result)
        post = heading + r2

    if isinstance(response, str):
        response = format_content(response)
        post = heading + response

    logger.info("posting to channel...")

    chunks = chunk_string(post, max_length=2000)

    for chunk in chunks:
        json_result = {"content": chunk}
        msg_resp = requests.post(url=webhook, json=json_result)
