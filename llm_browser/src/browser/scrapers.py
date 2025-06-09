"""Specific scraping logic"""

import logging
import os
import time

import requests
from dotenv import load_dotenv
from playwright.async_api import BrowserContext, Error, Page
from tqdm import tqdm

from llm_browser.src.browser.core import setup_browser_instance
from llm_browser.src.utils import set_logging

load_dotenv()

set_logging()
logger = logging.getLogger(__name__)

LINKEDIN_USERNAME = os.environ.get("LINKEDIN_USERNAME")
LINKEDIN_PASSWORD = os.environ.get("LINKEDIN_PASSWORD")


async def check_captcha(page: Page):
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
        [await page.is_visible(selector) for selector in captcha_selectors]
    )
    return has_captcha


async def fetch_google(url: str, context: BrowserContext, limit: int = None):
    """Download and process content from a URL

    Args
    ---
    prompt_content: a record containing the url, title, query, etc.
    headless: boolean indicating whether to use a headless browser
    """

    page = await context.new_page()
    await page.goto(url)

    # check for captcha challenge
    has_captcha = await check_captcha(page)
    if has_captcha:
        await page.pause()

    await page.wait_for_selector("body")

    # scroll to load all jobs
    max_scrolls = 5

    for _ in range(max_scrolls):
        await page.mouse.wheel(0, 10000)
        time.sleep(2)
        end_marker = page.get_by_text("No more jobs match your exact")
        if await end_marker.is_visible():
            logger.info("Reached end of page.")
            break

    links = await page.query_selector_all(selector="div.tNxQIb.PUpOsf")
    entities_element = await page.query_selector_all("div.wHYlTd.MKCbgd.a3jPc")
    entities = []
    for e in entities_element:
        entities.append(await e.text_content())

    if len(links) == 0:
        logger.warning("there was an issue extracting links")

    result = []

    limit = limit if limit is not None else len(links)

    counter = 0
    for i, (link, entity) in enumerate(zip(links, entities)):
        await link.click()
        counter += 1
        if counter > limit:
            logger.warning(f"Exceeded {limit=}")
            break

        try:
            await page.get_by_role(
                role="button", name="Show full description"
            ).click(timeout=10000)
            await page.wait_for_load_state("domcontentloaded")

            job_title = await link.text_content()

            descriptions = await page.query_selector_all("div.NgUYpe")
            current_desc = []
            for jd in descriptions:
                jd_text = await jd.text_content()
                if jd_text != "Report this listing":
                    current_desc.append(jd_text)

            if i == 0:
                result.append(
                    {
                        "title": job_title.strip(),
                        "company": entity.strip(),
                        "description": current_desc[0].strip(),
                    }
                )
            else:
                result.append(
                    {
                        "title": job_title.strip(),
                        "company": entity.strip(),
                        "description": current_desc[1].strip(),
                    }
                )

        except Exception as e:
            logger.exception(f"error on '{url}': {e}")

        logger.info(f"successfully retrieved '{job_title}' content")

    return result


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


async def get_job_cards(page: Page, limit: int = None):
    """
    Extract job details from search results.
    """
    res = []

    job_cards_locator = "div.scaffold-layout__list > div > ul > li"
    await page.wait_for_selector(job_cards_locator)

    # scroll to load all jobs
    max_scrolls = 5

    for _ in range(max_scrolls):
        await page.mouse.wheel(0, 10000)
        time.sleep(2)
        end_marker = page.get_by_role("button", name="View next page")
        if await end_marker.is_visible():
            logger.info("Reached end of page.")
            break

    job_cards = page.locator(job_cards_locator)
    jobs_count = await job_cards.count()
    logger.info(f"found {jobs_count} jobs")

    limit = limit if limit is not None else jobs_count

    for i in tqdm(range(limit)):
        job_details = ".jobs-box__html-content#job-details"
        card = job_cards.nth(i)
        await card.click()
        await page.wait_for_selector(job_details)
        job_title = card.locator(".job-card-container__link strong")
        company_name = card.locator(".artdeco-entity-lockup__subtitle span")
        location_name = card.locator(".artdeco-entity-lockup__caption li span")
        title = await job_title.inner_text() if job_title else "N/A"
        try:
            company = (
                await company_name.inner_text() if company_name else "N/A"
            )
        except Error:
            company = await company_name.nth(0).inner_text()
        except Exception as e:
            logger.exception(e)
        location = await location_name.inner_text() if location_name else "N/A"
        job_description_element = await page.query_selector(job_details)
        job_description = await job_description_element.inner_text()

        try:
            assert len(job_description) > len("About us") * 5
        except AssertionError:
            time.sleep(2)
            job_description = await job_description_element.inner_text()

        res.append(
            {
                "title": title.strip(),
                "company": company.strip(),
                "location": location.strip(),
                "description": job_description.strip(),
            }
        )
    return res


async def fetch_linkedin(
    url: str,
    context: BrowserContext,
    home_page: str = "https://www.linkedin.com/",
    login_success: str = "https://www.linkedin.com/feed/",
    max_pages: int = 10,
    limit: int = None,
):
    """
    Fetches LinkedIn job listings, including pagination, when logged in.
    """
    results = []
    page = await context.new_page()
    logger.info(f"Navigating to {home_page=}")
    await page.goto(home_page, wait_until="domcontentloaded")
    current_page = page.url
    if current_page == login_success:
        logger.info("Already logged in")
    else:
        await page.locator('[data-test-id="home-hero-sign-in-cta"]').click()
        await page.get_by_role("textbox", name="Email or phone").fill(
            LINKEDIN_USERNAME
        )
        await page.get_by_role("textbox", name="Password").fill(
            LINKEDIN_PASSWORD
        )
        await page.get_by_role("button", name="Sign in", exact=True).click()
        await page.wait_for_url(login_success, wait_until="domcontentloaded")

    logger.info(f"Navigating to: {url=}")
    await page.goto(url, wait_until="domcontentloaded")

    if limit is not None:
        res = await get_job_cards(page, limit)
        return res

    current_page_num = 1
    while current_page_num <= max_pages:
        logger.info(f"Processing page {current_page_num}...")
        res = await get_job_cards(page)
        results.extend(res)
        next_button = await page.locator('button[aria-label="View next page"]')
        if next_button.is_visible() and not next_button.is_disabled():
            logger.info("Clicking 'Next' button to navigate to the next page.")
            try:
                await next_button.click()
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_selector(".job-card-container")
                res = await get_job_cards(page)
                current_page_num += 1
            except Exception as e:
                logger.error(f"Error navigating to next page: {e}")
                break
        else:
            logger.info(
                "'Next' button not visible or disabled. End of pagination."
            )
            break

        logger.info(
            f"Finished fetching jobs. Total jobs extracted: {len(results)}"
        )
    logger.info(f"total jobs extracted: {len(results)}")
    return results
