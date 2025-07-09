from pymongo import MongoClient
from credentials.vfcfg import *
import json

# Load JSON files
json_paths = [
    "C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/review_results/trees/2025-07-09_16-48-21--686e0cb099a8bf938dc2aab1.json",
    "C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/review_results/trees/2025-07-09_16-50-34--686cd28040209effb126ac8d"
]

#TODO
# Connect to MongoDB
client = MongoClient(mongo_uri)
db = client[db_name]
colResult = db[collection_result]

# Process each JSON file
for path in json_paths:
    with open(path, "r") as f:
        record = json.load(f)

    email_info = record.get("email_info", {})
    main_items = record.get("main", [])
    sub_items = record.get("sub", [])

    # Helper to upsert each item
    def upsert_items(items, item_type):
        for item in items:
            filter_query = {
                "email_id": item["email_id"],
                "question_id": item["question_id"],
                "type": item_type  # distinguish between 'main' and 'sub'
            }
            update_doc = {
                "$set": {
                    "email_info": email_info,
                    "question": item,
                    "type": item_type
                }
            }
            colResult.update_one(filter_query, update_doc, upsert=True)

    upsert_items(main_items, "main")
    upsert_items(sub_items, "sub")