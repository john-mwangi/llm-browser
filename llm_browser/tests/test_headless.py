import json
import os

import pytest
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from llm_browser.src.browser.scrapers import (
    fetch_linkedin,
    fetch_linkedin_logged_out,
)
from llm_browser.src.configs.config import ROOT_DIR, browser_args

load_dotenv()


@pytest.mark.skip
def test_headless(
    url: str = "https://arh.antoinevastel.com/bots/areyouheadless",
):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=browser_args)
        page = browser.new_page()
        page.goto(url=url, wait_until="networkidle")
        answer = page.locator("#res").text_content()

        # required xvfb to work in headless
        assert answer == "You are not Chrome headless"


@pytest.mark.skip
def test_google_search():
    GOOGLE_PSE_API_KEY = os.environ.get("GOOGLE_PSE_API_KEY")
    GOOGLE_PSE_ID = os.environ.get("GOOGLE_PSE_ID")
    q = os.environ.get("GOOGLE_SEARCH_QUERY")

    response = requests.get(
        f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_PSE_API_KEY}&cx={GOOGLE_PSE_ID}&q={q}"
    )
    byte_data = response.content
    json_str = byte_data.decode("utf-8")
    data = json.loads(json_str)

    results_dir = ROOT_DIR / "results"
    file_name = "google_search_results"
    file_path = os.path.join(results_dir, file_name)

    with open(file_path, mode="w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def test_linkedin(loggedin=[True]):

    urls = [
        "https://www.linkedin.com/jobs/search/?currentJobId=4179406112&distance=25&f_TPR=r604800&geoId=100710459&keywords=(analytics%20OR%20%22data%20science%22%20OR%20%22business%20intelligence%22%20OR%20%22data%20strategy%22%20OR%20%22data%20governance%22%20OR%20%22data%20engineer%22%20OR%20%22machine%20learning%22)%20NOT%20%22Lumenalta%22&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true",
        "https://www.linkedin.com/jobs/search/?currentJobId=4219865496&distance=25&f_TPR=r604800&f_WT=2&geoId=104035573&keywords=(analytics%20OR%20%22data%20science%22%20OR%20%22business%20intelligence%22%20OR%20%22data%20strategy%22%20OR%20%22data%20governance%22%20OR%20%22data%20engineer%22%20OR%20%22machine%20learning%22)%20NOT%20%22Lumenalta%22&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true",
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=browser_args)
        context = browser.new_context()

        for url in urls:
            if False in loggedin:
                data = fetch_linkedin_logged_out(url=url)
            if True in loggedin:
                data = fetch_linkedin(url=url, limit=1, context=context)
                item = data[0][0]
                keys_ = item.keys()
                result_keys = [
                    "title",
                    "company",
                    "location",
                    "description",
                ]

                assert all([k in result_keys for k in keys_])
                assert len(item["description"]) > len("About us") * 5
