"""Specific scraping logic"""

import logging
import os

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import Page, sync_playwright

from llm_browser.src.configs.config import browser_args, results_dir
from llm_browser.src.utils import set_logging

set_logging()
logger = logging.getLogger(__name__)


def check_captcha(page: Page):
    """Checks if a page as a captcha challenge"""

    captcha_selectors = [
        ".g-recaptcha",
        "#recaptcha",
        "#hcaptcha",
        ".h-captcha",
        'iframe[src*="recaptcha"]',
        'iframe[src*="hcaptcha"]',
    ]

    has_captcha = any(
        [page.is_visible(selector) for selector in captcha_selectors]
    )
    return has_captcha


def download_content_google(prompt_context: dict, headless: bool):
    """Download and process content from a URL

    Args
    ---
    prompt_content: a record containing the url, title, query, etc.
    headless: boolean indicating whether to use a headless browser
    """
    url = prompt_context["url"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=browser_args)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.75 Safari/537.36",
            locale="en-US",
            permissions=["notifications"],
        )
        # page = context.new_page()
        page = browser.new_page()
        page.goto(url)

        # check for captcha challenge
        has_captcha = check_captcha(page)
        if has_captcha:
            page.pause()

        page.is_visible()

        page.wait_for_selector("body")

        links = page.query_selector_all(selector="div.tNxQIb.PUpOsf")
        entities = page.query_selector_all("div.wHYlTd.MKCbgd.a3jPc")
        entities = [e.text_content().strip() for e in entities]

        if len(links) == 0:
            logger.warning("there was an issue extracting links")

        data = {}

        for link, entity in zip(links, entities):
            link.click()

            try:
                page.get_by_role(
                    role="button", name="Show full description"
                ).click(timeout=5000)
                page.wait_for_load_state("domcontentloaded")
                content = page.query_selector("div.NgUYpe").text_content()
                data[link.text_content()] = f"Entity: {entity}\n\n" + content

            except Exception as e:
                logger.exception(f"error on '{link.text_content()}': {e}")
                data[link.text_content()] = f"Entity: {entity}\n\n"

            logger.info(
                f"successfully retrieved '{link.text_content()}' content"
            )

        context.close()
        browser.close()
        return data


def query_google(data: dict, prompt: str, model):
    """Queries an LLM model

    Args
    ---
    data: results of the scraping process
    prompt: the prompt to use
    model: the LangChain model

    Returns
    ---
    An API response
    """

    logger.info("querying llm...")

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

    model_name = model.model.split("/")[-1]

    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
        params=params,
        headers=headers,
        json=json_data,
    )

    return response


def extract_transcript(url: str):
    """Extracts the Fireflies transcript

    Args
    ---
    url: of the Fireflies transcript
    """

    meeting_name = url.split("::")[0].split("/")[-1]
    file_name = f"{meeting_name}.txt"
    file_path = os.path.join(results_dir, file_name)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector(".paragraph-root")
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    paragraphs = soup.find_all("div", class_="paragraph-root")

    markdown_output = []

    for para in paragraphs:
        # Extract name
        name_span = para.find("span", class_="name")
        name = name_span.text.strip() if name_span else "Unknown"

        # Extract timestamp
        timestamp_span = para.find("span", class_="sc-871c1b8d-0")
        timestamp = timestamp_span.text.strip() if timestamp_span else "00:00"

        # Extract message
        message_div = para.find("div", class_="transcript-sentence")
        message = message_div.text.strip() if message_div else ""

        # Format the line
        markdown_line = f"{name} - {timestamp}\n{message}\n"
        markdown_output.append(markdown_line)

    with open(file_path, "w") as f:
        f.writelines(markdown_output)
