"""Truly generic helper functions"""

import functools
import json
import logging
import os
import re
import time
from typing import Any, Callable, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()

WEB_HOOK = os.environ.get("DISCORD_WEBHOOK")
REQ_PER_SEC = 50
MIN_DELAY_SEC = 0.1


def set_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        force=True,
    )


def chunk_string(input_string, max_length):
    """Split a string into chunks of specified maximum length"""
    chunks = []
    while input_string:
        chunks.append(input_string[:max_length])
        input_string = input_string[max_length:]
    return chunks


def split_string(input_string: str, sep: str):
    chunks = input_string.split(sep)
    return chunks


def format_content(content: str) -> str:
    r1 = re.sub(r"\n{2,}", "\n", content, flags=re.MULTILINE)
    r2 = re.sub(r"^#\s*(.+?)\s*$", r"\n**\1**", r1, flags=re.MULTILINE)
    return r2


def post_response(content: str, webhook: str, title: str):
    """Posts to a Discord, WhatApp, Slack, etc. using the webhook

    Args
    ---
    content: the content to post
    webhook: the webhook to post to
    title: the title of the post
    """
    heading = f"# Postings for: **{title.title()}**\n\n"
    content = format_content(content)
    post = heading + content
    chunks = split_string(post, sep="\n\n")
    delay = 60 / (REQ_PER_SEC * 60) + MIN_DELAY_SEC

    for chunk in chunks:
        json_result = {"content": chunk}
        msg_resp = requests.post(url=webhook, json=json_result)
        time.sleep(delay)


def post_notification(webhook: str = WEB_HOOK):
    """Decorator that posts the results of a function to a channel

    Args
    ---
    - webhook: the webhook to post a message to.
    """

    def decorator(func: Callable[..., Tuple[str, str]]):

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result, title = func(*args, **kwargs)

            # post result to webhook
            post_response(content=result, webhook=webhook, title=title)

            return result

        return wrapper

    return decorator


def string_to_dict(texts: list[str]):
    for text in texts:
        try:
            text = text.split("```json")[1].split("```")[0].strip()
            fixed_json = re.sub(r"(\\n|\n)\s*|\\", "", text)
            json_res: dict = json.loads(fixed_json)
            return json_res
        except Exception as e:
            continue
    raise ValueError("could not parse json")
