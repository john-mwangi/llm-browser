import json
import os

import pytest
import requests
from bson import ObjectId
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

from llm_browser.src.browser.scrapers import (
    fetch_google,
    fetch_linkedin,
    fetch_linkedin_logged_out,
)
from llm_browser.src.configs.config import ROOT_DIR, browser_args
from llm_browser.src.database import get_mongodb_client

load_dotenv()


@pytest.mark.skip(reason="requires xvfb to work in headless")
def test_headless(
    url: str = "https://arh.antoinevastel.com/bots/areyouheadless",
):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=browser_args)
        page = browser.new_page()
        page.goto(url=url, wait_until="networkidle")
        answer = page.locator("#res").text_content()
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


@pytest.mark.asyncio
async def test_fetch_linkedin(loggedin=[True], limit=2):
    db_name = os.environ.get("_MONGO_DB")
    collection_name = os.environ.get("CONTEXT_NAME")
    ids = [
        ObjectId(i)
        for i in [
            "68128e1796cefad9b2cd1bc7",
            "6812962096cefad9b2cd1bc9",
            "681299be96cefad9b2cd1bcd",
            "68129a3f96cefad9b2cd1bcf",
        ]
    ]

    client = get_mongodb_client()
    with client:
        db = client[db_name]
        collection = db[collection_name]
        docs = collection.find({"_id": {"$in": ids}})
        urls = [doc["url"] for doc in docs]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=browser_args)
        context = await browser.new_context()

        for url in urls:
            if False in loggedin:
                data = fetch_linkedin_logged_out(url=url)
            if True in loggedin:
                data = await fetch_linkedin(
                    url=url, limit=limit, context=context
                )
            item = data[0]
            keys_ = item.keys()
            result_keys = [
                "title",
                "company",
                "location",
                "description",
            ]

            assert all([k in result_keys for k in keys_])
            assert len(item["description"]) > len("About us") * 5


@pytest.mark.asyncio
async def test_fetch_google(limit=2):
    db_name = os.environ.get("_MONGO_DB")
    collection_name = os.environ.get("CONTEXT_NAME")
    ids = [
        ObjectId(i)
        for i in ["67f7e626ceb330e99ad861e0", "67fe8adbfae9e89e0dba5b91"]
    ]

    client = get_mongodb_client()
    with client:
        db = client[db_name]
        collection = db[collection_name]
        docs = collection.find({"_id": {"$in": ids}})
        urls = [doc["url"] for doc in docs]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=browser_args)
        context = await browser.new_context()

        for url in urls:
            data = await fetch_google(url=url, limit=limit, context=context)
            item = data[0]
            keys_ = item.keys()
            result_keys = [
                "title",
                "company",
                "description",
            ]

            assert all([k in result_keys for k in keys_])
            assert len(item["description"]) > len("Job description") * 5
