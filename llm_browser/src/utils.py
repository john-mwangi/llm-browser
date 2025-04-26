"""Truly generic helper functions"""

import logging


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
