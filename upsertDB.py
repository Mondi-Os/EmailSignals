from pymongo import MongoClient
from credentials.vfcfg import *
import json

# Load JSON files
json_paths = [
    "C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/review_results/2025-07-10_16-50-34--686cd28040209effb126ac8d.json",
]

client = MongoClient(mongo_uri)
db = client[db_name]
colResult = db[collection_result]
# TODO --> When MongoDB software is installed - check if text preprocessing is needed (eg., '\n'.....)
# TODO --> The code below might need to change if we want to upsert to MongoDB the records right away without saving them to JSON files first.

# Upsert JSON records into MongoDB collection
# for path in json_paths:
#     with open(path, "r") as f:
#         record = json.load(f)
#     colResult.insert_one(record)

client = MongoClient(mongo_uri)
db = client[db_name]
collection = db[collection_result]

# Fetch all documents
all_items = list(collection.find())

# Print each document
for item in all_items:
    print(item)