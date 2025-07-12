import json
import os
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
    print(all_items)

    return all_items


def upsert_into_mongo_based_on_question_hashes(collection_name, json_paths):
    """Upsert each question from the JSON file into MongoDB based on its unique hash."""
    client = MongoClient(mongo_uri)
    db = client[db_name]
    col_llm_cache = db[collection_name]

    for path in json_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                record = json.load(f)

            questions = record.get("questions", [])

            for q in questions:
                q_hash = q.get("hash")
                if not q_hash:
                    print(f"Skipping question (missing hash) in: {os.path.basename(path)}")
                    continue

                # Extract answer
                answer_content = q.get("response", {}).get("response", {}) \
                    .get("output", {}).get("message", {}).get("content", [])

                if isinstance(answer_content, list) and len(answer_content) > 0:
                    first = answer_content[0]
                    if isinstance(first, dict):
                        answer = first.get("text") or first.get("solution") or ""
                    else:
                        answer = str(first)
                else:
                    answer = ""
                # Upsert each question individually based on its hash
                result = col_llm_cache.update_one(
                    {"hash": q_hash},
                    {"$set": {
                        "hash": q_hash,
                        "question": q["question"],
                        "answer": answer
                    }},
                    upsert=True
                )

                if result.matched_count:
                    print(f" Updated question with hash: {q_hash}")
                else:
                    print(f" Inserted new question with hash: {q_hash}")

        except Exception as e:
            print(f"Failed to process {path}: {e}")