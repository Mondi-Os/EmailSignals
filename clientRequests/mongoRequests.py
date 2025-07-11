import json
from credentials.vfcfg import *
from clientRequests.dataPreprocessing import *
from pymongo import MongoClient

def fetch_emails_from_database(filter_dict={}, limit=1):
    """Fetch emails from MongoDB and clean the email body."""
    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db[collection_mail]

    # Fetch documents from the collection with the specified filter and limit
    documents = collection.find(filter_dict, {
        "_id": 1,
        "date": 1,
        "from": 1,
        "body": 1
    }).sort("_id", -1).limit(limit)

    # Clean emails and keep the relevant fields
    cleaned_docs = []
    for doc in documents:
        cleaned_docs.append({
            "_id": str(doc["_id"]),
            "date": doc.get("date"),
            "from": doc.get("from"),
            "body": clean_email_body(doc.get("body", ""))
        })

    return cleaned_docs


def read_collection(collection_name: str):
    """Read and print all documents from a MongoDB collection."""
    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db[collection_name]

    # Fetch all documents
    all_items = list(collection.find())

    # Print each document
    for item in all_items:
        print(f"\n{item}")
    pass


# TODO --> When MongoDB software is installed - check if text preprocessing is needed (eg., '\n'.....)
# TODO --> The code below might need to change if we want to upsert to MongoDB the records right away without saving them to JSON files first.
def insert_into_mongo(collection_name, json_paths):
    """Insert JSON records into a MongoDB collection."""
    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client[db_name]
    colection_llm_cache = db[collection_name]

    # Upsert JSON records into MongoDB collection
    for path in json_paths:
        with open(path, "r") as f:
            record = json.load(f)
        colection_llm_cache.insert_one(record)
    pass
