"""MongoDB client setup, functions to interact with collections"""

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()


def get_mongodb_client():
    """Establishes a MongoDB client

    Returns
    ---
    Tuple of (MongoClient, database_name)
    """

    _USER = os.environ.get("_MONGO_UNAME")
    _PASSWORD = quote_plus(os.environ.get("_MONGO_PWD"))
    _HOST = os.environ.get("_MONGO_HOST")
    _PORT = os.environ.get("_MONGO_PORT")

    uri = f"mongodb://{_USER}:{_PASSWORD}@{_HOST}:{_PORT}/"

    return MongoClient(uri)


def save_to_db(fp: Path | str | None, key: str, collection: str, data: dict):
    """Inserts a document from a file into the database. The content of your
    file will be added to `data`

    Args
    ---
    - fp: the file path to the document or multiline string
    - key: the key to associate the file contents with
    - collection: the name of the collection to add this file to
    - data: additional data content to add to fp

    Example
    ---
    This will upload as: `{"prompt": prompt, "type": "filter_roles"}`

    ```
    file_to_db(
        fp=prompt,
        key="prompt",
        collection="prompts",
        data={"type": "filter_roles"},
    )
    ```
    """

    db_name = os.environ.get("_MONGO_DB")
    client = get_mongodb_client()

    with client:
        db = client[db_name]
        coll = db[collection]

        if fp is None:
            coll.insert_one(data)
            print(f"\nUploaded successfully to {collection=}")
            return

        elif isinstance(fp, Path):
            with open(fp) as f:
                value = f.read()
                content = {key: value}

        elif isinstance(fp, str):
            content = {key: fp}

        else:
            raise ValueError("unsupported fp!")

        document = {**data, **content}
        coll.insert_one(document)

    print(f"\nUploaded successfully to {collection=}")
