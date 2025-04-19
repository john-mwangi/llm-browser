import json
import os
import sys

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.utils import ROOT_DIR, download_content_google, get_mongodb_client

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
    data = download_content_google(prompt_context={"url": url}, headless=headless)


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


def insert_multiline_doc(fp, collection, key, name):
    """Inserts a multiline document from a file

    Args
    ---
    fp: the file path to the document
    collection: the name of the collection
    key: they type of document
    name: the name of the document
    """

    client, db_name = get_mongodb_client()
    db = client[db_name]
    coll = db[collection]

    with open(fp) as f:
        content = f.read()

    coll.insert_one({"type": name, key: content})
