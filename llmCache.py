import hashlib
from clientRequests.mongoRequests import *
import os

# Load JSON files
json_paths = [
    "C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/review_results/2025-07-10_18-18-14--686f602699a8bf938dc2ab37.json",
    "C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/review_results/2025-07-10_18-21-19--686e0cb099a8bf938dc2aab1.json",
    "C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/review_results/2025-07-10_18-29-56--686cd28040209effb126ac8d.json",
    "C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/review_results/2025-07-11_09-23-49--6870b38299a8bf938dc2aba8.json",
    "C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/review_results/2025-07-11_09-18-01--6870c4b399a8bf938dc2abb5.json",
]

def add_hash_to_emails(json_paths):
    """Add or verify hash in each email file based on email_info['date'] and ['from']."""
    for path in json_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            email_info = data.get("email_info", {})
            date = email_info.get("date", "")
            sender = email_info.get("from", "")
            hash_input = f"{date}|{sender}"
            new_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

            existing_hash = data.get("hash")

            if existing_hash:
                if existing_hash == new_hash:
                    print(f"Hash already exists and matches for: {os.path.basename(path)}")
                    continue  # skip rewriting the file
                else:
                    print(f"Hash mismatch in: {os.path.basename(path)} — updating...")

            # Add or update the hash field
            updated_data = {
                "hash": new_hash,
                "email_info": email_info,
                "questions": data.get("questions", [])
            }

            with open(path, "w", encoding="utf-8") as f:
                json.dump(updated_data, f, indent=2, ensure_ascii=False)

            print(f"Hash written to: {os.path.basename(path)}")

        except Exception as e:
            print(f"Failed to process {path}: {e}")

add_hash_to_emails(json_paths)



#TODO for the end
# # Insert JSON records into MongoDB collection
# insert_into_mongo("llm_cache", json_paths)

# Read the database and print the results
# col_llm_cache = read_collection(collection_llm_cache)