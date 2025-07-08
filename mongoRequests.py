from pymongo import MongoClient

# MongoDB connection details
mongo_uri = "mongodb://vernvlxpddec001.veritionfund.cloud"
db_name = "research"
collection_name = "mail"

# Connect to MongoDB
client = MongoClient(mongo_uri)
db = client[db_name]
collection = db[collection_name]

# Fetch the last 10 documents (sorted by _id descending)
last_10_docs = collection.find({}, {"_id": 1, "date": 1, "createdDateTime": 1,
                                          "from": 1, "body": 1, "bodyPreview": 1}
                               ).sort("_id", -1).limit(2)
all = collection.find().sort("_id", -1).limit(1)

# Print the documents
for doc in last_10_docs:
    print(doc)