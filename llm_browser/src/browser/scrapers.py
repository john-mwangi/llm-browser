"""Specific scraping logic"""

import logging
import os
import time

import requests
from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright
from tqdm import tqdm

from llm_browser.src.browser.core import setup_browser_instance
from llm_browser.src.configs.config import browser_args
from llm_browser.src.utils import set_logging

load_dotenv()

set_logging()
logger = logging.getLogger(__name__)

LINKEDIN_USERNAME = os.environ.get("LINKEDIN_USERNAME")
LINKEDIN_PASSWORD = os.environ.get("LINKEDIN_PASSWORD")


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


def fetch_google(url: str, headless: bool = False):
    """Download and process content from a URL

    Args
    ---
    prompt_content: a record containing the url, title, query, etc.
    headless: boolean indicating whether to use a headless browser
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
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

            logger.info(
                f"successfully retrieved '{link.text_content()}' content"
            )

    return data


def query_gemini(data: dict, prompt: str, model):
    """Queries a Gemini model

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

    result = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    return result


def fetch_linkedin_logged_out(url: str, headless: bool = False):
    """Scrape LinkedIn content"""

    browser, p = setup_browser_instance()
    browser = p.chromium.launch(headless=headless)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded")

    # handle page redirects
    if page.url != url:
        browser.close()
        p.stop()
        browser, p = setup_browser_instance()
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")

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

            job_description = (
                page.locator("div.description__text").text_content().strip()
            )

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

    browser.close()
    p.stop()
    return results


def get_job_cards(page: Page):
    """
    Extract job details from search results.
    """
    res = []
    try:
        page.wait_for_selector(
            "ul.UqvsszlKcsHVxKPENVjvrBhRdSmTopYxAtIreCY", timeout=10000
        )
    except Exception:
        logger.warning(
            "Main job list container not found. No jobs to extract on this page."
        )
        return []

    job_cards = page.locator(".job-card-container")
    for i in range(job_cards.count()):
        card = job_cards.nth(i)
        card.click()
        time.sleep(2)
        job_title = card.locator(".job-card-container__link strong")
        company_name = card.locator(".artdeco-entity-lockup__subtitle span")
        location_name = card.locator(".artdeco-entity-lockup__caption li span")
        title = job_title.inner_text() if job_title else "N/A"
        company = company_name.inner_text() if company_name else "N/A"
        location = location_name.inner_text() if location_name else "N/A"
        job_details = ".jobs-box__html-content#job-details"
        job_description = page.query_selector(job_details)
        res.append(
            {
                "title": title.strip(),
                "company": company.strip(),
                "location": location.strip(),
                "description": job_description.inner_text(),
            }
        )
    return res


def fetch_linkedin(
    url: str,
    headless: bool = False,
    home_page: str = "https://www.linkedin.com/",
    login_success: str = "https://www.linkedin.com/feed/",
    max_pages: int = 5,
):
    """
    Fetches LinkedIn job listings, including pagination, when logged in.
    """
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=browser_args)
        page = browser.new_page()
        logger.info(f"Navigating to {home_page=}")
        page.goto(home_page, wait_until="domcontentloaded")

        try:
            sign_in_cta = page.locator(
                '[data-test-id="home-hero-sign-in-cta"]'
            )
            if sign_in_cta.is_visible():
                logger.info("Clicking sign-in CTA.")
                sign_in_cta.click()
                page.wait_for_url("**/login*")
            else:
                logger.info("Already logged in.")
        except Exception as e:
            logger.warning(f"Could not find or click sign-in CTA: {e}")

        page.get_by_role("textbox", name="Email or phone").fill(
            LINKEDIN_USERNAME
        )
        page.get_by_role("textbox", name="Password").fill(LINKEDIN_PASSWORD)
        page.get_by_role("button", name="Sign in", exact=True).click()
        page.wait_for_url(login_success)
        logger.info(f"Navigating to: {url=}")
        page.goto(url, wait_until="domcontentloaded")

        current_page_num = 1
        while current_page_num <= max_pages:
            logger.info(f"Processing page {current_page_num}...")
            res = get_job_cards(page)
            results.extend(res)
            next_button = page.locator('button[aria-label="View next page"]')
            if next_button.is_visible() and not next_button.is_disabled():
                logger.info(
                    "Clicking 'Next' button to navigate to the next page."
                )
                try:
                    next_button.click()
                    page.wait_for_load_state("domcontentloaded")
                    page.wait_for_selector(
                        ".job-card-container", timeout=10000
                    )
                    current_page_num += 1
                except Exception as e:
                    logger.error(f"Error navigating to next page: {e}")
                    break
            else:
                logger.info(
                    " 'Next' button not visible or disabled. End of pagination."
                )
                break

        logger.info(
            f"Finished fetching jobs. Total jobs extracted: {len(results)}"
        )
        browser.close()
    return results
