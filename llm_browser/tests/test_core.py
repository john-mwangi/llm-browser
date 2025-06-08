import asyncio
import json
import os

from bson import ObjectId
from dotenv import load_dotenv

from llm_browser.src.browser.core import browse_content
from llm_browser.src.database import get_mongodb_client
from llm_browser.src.llm.models import models

load_dotenv()


def test_browse_content():
    db_name = os.environ.get("_MONGO_DB")
    ids = [ObjectId(i) for i in ["68248c86bda0e87a5375d260"]]
    vision_model = os.environ.get("VISION_MODEL")
    context_name = os.environ.get("CONTEXT_NAME")

    client = get_mongodb_client()
    with client:
        db = client[db_name]
        collection = db["prompts"]
        docs = collection.find({"_id": {"$in": ids}})
        prompt = [doc["prompt"] for doc in docs][0]
        context = db[context_name]
        url = context.find_one({"task": "browse"})["url"]

    browsing_prompt = prompt + "\n\nURL to navigate: " + url
    agent_history = asyncio.run(
        browse_content(
            prompt=browsing_prompt,
            model=models.get(vision_model),
        )
    )

    result = agent_history.final_result()
    result_keys = [
        "job_title",
        "location",
        "company_name",
        "company_description",
        "role_requirements",
        "skills_required",
        "experience_required",
    ]

    data = json.loads(result)
    item = data[0]
    keys_ = item.keys()
    assert all([k in result_keys for k in keys_])
    assert len(item["role_requirements"]) > len("Job description") * 5
