from pymongo import MongoClient


# Client credentials for VF Core API
APP = 'vf.python.client'
URI = 'vf-core-api.veritionfund.cloud:30070'
USER = 'rjohnsonperkins'
TOKEN = 'ZNMmSyIpxHUSobVGIkHKQLaXe/XWGn00WiQZj2RXKi1uI5yS0dmIqeYnDj4Mz5CeaBU0xy5NN9+g4bAVQ9GqUvB/dC87kObDEbpvA9KXYInK2KJFWaZpUuuH+DY60fVNF4JFIDxyOXtPsZ5EKmyOWpd0QafIGJyL9bqAIIvp8Ag='

# MongoDB VF
mongo_uri = "mongodb://vernvlxpddec001.veritionfund.cloud" # MongoDB URI
db_name = "research" # Database name
client = MongoClient(mongo_uri) # Create MongoDB client
db = client[db_name] # Access the database

email_collection = db["mail"]  # Collection: Email from Outlook
result_collection = db["result"] # Collection: LLM results
prompts_collection = db["promptsFramework"] # Collection: promptsFramework to ask the LLM


# MongoDB Local
mongo_uri_local = "mongodb://localhost:27017/"
client_local = MongoClient(mongo_uri_local)
db_local = client_local["admin"]

llm_cache_collection_local = db_local["llm_cache"]