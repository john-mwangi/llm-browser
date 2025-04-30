"""Specific scraping logic"""

import logging
import os
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright
from tqdm import tqdm

from llm_browser.src.browser.core import setup_browser_instance
from llm_browser.src.configs.config import results_dir
from llm_browser.src.utils import set_logging

load_dotenv()

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


def download_content_google(url: str):
    """Download and process content from a URL

    Args
    ---
    prompt_content: a record containing the url, title, query, etc.
    headless: boolean indicating whether to use a headless browser
    """

    browser, playwright = setup_browser_instance()
    page = browser.new_page()
    page.goto(url)

    # check for captcha challenge
    has_captcha = check_captcha(page)
    if has_captcha:
        page.pause()

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
            data[link.text_content()] = f"Company: {entity}\n\n" + content

        except Exception as e:
            logger.exception(f"error on '{link.text_content()}': {e}")
            data[link.text_content()] = f"Company: {entity}\n\n"

        logger.info(f"successfully retrieved '{link.text_content()}' content")

    browser.close()
    playwright.stop()
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
    file_path = results_dir / file_name

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
        markdown_line = f"{name} - {timestamp}\n{message}\n\n"

        markdown_output.append(markdown_line)

    with open(file_path, "w") as f:
        f.writelines(markdown_output)

    logger.info(f"transcript saved to {file_path.resolve()}")


def download_content_linkedin(url: str):
    """Scrape LinkedIn content"""

    browser, p = setup_browser_instance()
    page = browser.new_page()
    page.goto(url)
    page.get_by_role("button", name="Dismiss").click()
    page.wait_for_selector("ul.jobs-search__results-list")

    # scroll to load all jobs
    max_scrolls = 20

    for _ in range(max_scrolls):
        page.mouse.wheel(0, 10000)
        time.sleep(2)

        see_more = page.get_by_role("button", name="See more jobs")
        if see_more.is_visible():
            see_more.click()
            time.sleep(2)

        end_marker = page.locator(
            'div.see-more-jobs__viewed-all:has-text("You\'ve viewed all jobs for this search")'
        )

        if end_marker.is_visible():
            logger.info("Reached end of job listings.")
            break

    # loaded jobs
    cards = page.locator("ul.jobs-search__results-list li")
    count = cards.count()
    logger.info(f"Total jobs collected: {count}")

    results = []

    for i in tqdm(range(count)):
        card = cards.nth(i)
        card.click()

        try:
            page.get_by_role("button", name="Apply").wait_for(timeout=10000)
            show_more = page.locator('button:has-text("Show more")')
            if show_more.is_visible():
                show_more.click()
                # page.wait_for_timeout(1000)

            desc_element = page.locator("div.description__text")
            desc_html = desc_element.inner_html()
            desc_soup = BeautifulSoup(desc_html, "html.parser")
            job_description = desc_soup.get_text(strip=True)

        except Exception as e:
            job_description = ""

        # extract details
        title = (
            card.locator("h3.base-search-card__title").text_content().strip()
        )
        company = (
            card.locator("h4.base-search-card__subtitle")
            .text_content()
            .strip()
        )
        location = (
            card.locator("span.job-search-card__location")
            .text_content()
            .strip()
        )
        # url = card.locator("a.base-card__full-link").get_attribute("href")

        results.append(
            {
                "title": title,
                "company": company,
                "location": location,
                "description": job_description,
            }
        )

    page.close()
    p.stop()

    return results
