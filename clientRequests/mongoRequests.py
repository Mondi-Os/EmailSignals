from pymongo import MongoClient
import json
from credentials.vfcfg import *
from clientRequests.dataPreprocessing import *

# Connect to MongoDB
client = MongoClient(mongo_uri)
db = client[db_name]
collection = db[collection_name]

# Fetch documents - request specific keys
last_2_docs = collection.find({"from": "ewan.gordon@socgen.com"}, { #filter here if needed: "from": "ewan.gordon@socgen.com"
    "_id": 1,
    "date": 1,
    "from": 1,
    "body": 1,
    }).sort("_id", -1).limit(5)

# Build cleaned JSON
cleaned_docs = []
for doc in last_2_docs:
    cleaned_doc = {
        "_id": str(doc["_id"]),
        "date": doc.get("date"),
        "from": doc.get("from"),
        "body": clean_email_body(doc.get("body", ""))
    }
    cleaned_docs.append(cleaned_doc)

# Output as JSON
single_email_info = json.dumps(cleaned_docs, indent=2)

# Convert JSON string back to list of dicts
parsed_docs = json.loads(single_email_info)

# Access the first document’s body
email_info = [{"_id": doc["_id"],
               "date": doc["date"],
               "from": doc["from"],
               "body": doc["body"]
               } for doc in parsed_docs]

# Access the first document’s body
email_body = email_info[0]["body"]

#TODO remove printing statements

# print(email_body)
# # Print the email information
# for info in email_info:
#     print(info)