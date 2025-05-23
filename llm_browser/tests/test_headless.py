import json
import os
import sys

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

sys.path.append("../")
from src.utils import ROOT_DIR, fetch_google

load_dotenv()


def test_stealth(url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
        )
        page = browser.new_page()
        stealth_sync(page)
        page.goto(url=url, wait_until="networkidle")
        browser.close()


def test_download_content():
    url = os.environ.get("GOOGLE_SEARCH_URL")
    headless = os.environ.get("HEADLESS")
    data = fetch_google(prompt_context={"url": url}, headless=headless)


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
