import queue
import threading
from datetime import timedelta
import time
from llm_helpers.llmPipeline import *

email_queue = queue.Queue()
seen_ids = set()
seen_lock = threading.Lock()

def get_recent_unprocessed_emails():
    """Fetches emails from the last 1 day that have not been processed by the LLM, based on _id in 'mail' and source_id in 'result'."""
    cutoff_str = (datetime.now() - timedelta(days=1)).isoformat()

    # Get recent emails (_id from mail collection)
    recent_emails = list(email_collection.find(
        {"date": {"$gte": cutoff_str}},
        {"_id": 1}
    ))

    # Extract just the _ids
    recent_ids = [doc["_id"] for doc in recent_emails]

    # Find which of these _ids already exist in result.source_id
    processed_source_ids = set(doc["source_id"] for doc in result_collection.find(
        {"source_id": {"$in": recent_ids}},
        {"source_id": 1}
    ))

    # Return only those _ids not found in result
    unprocessed = [email_id for email_id in recent_ids if email_id not in processed_source_ids]
    return unprocessed


def fetch_emails_by_ids(ids):
    """Fetches emails by their IDs from the email collection."""
    documents = email_collection.find({"_id": {"$in": ids}})
    return [{
        "_id": str(doc["_id"]),
        "date": doc.get("date"),
        "from": doc.get("from"),
        "body": clean_email_body(doc.get("body", ""))
    } for doc in documents]


def email_worker():
    """Worker thread to process emails from the queue."""
    while True:
        email_id = email_queue.get()
        try:
            email = fetch_emails_by_ids([email_id])
            if email:
                pipeline = LLMPipeline()
                pipeline.run_batch(email)
        except Exception as e:
            print(f"\033[1;31mError processing email {email_id}: {e}\033[0m")
        finally:
            email_queue.task_done()


def change_listener():
    """Listens for changes in the 'email' collection and queues new emails."""
    with email_collection.watch(full_document="updateLookup") as stream:
        print("Listening for changes in the 'mail' collection...\n")
        for change in stream:
            op_type = change.get("operationType")
            email_id = change["documentKey"]["_id"]
            full_doc = change.get("fullDocument", {})

            print(f"Change Detected in the 'mail' collection ({op_type.upper()}):", {"_id": str(email_id), "date": full_doc.get("date"), "from": full_doc.get("from")})

            # Queue for processing
            if op_type in {"insert"}:
                with seen_lock:
                    if email_id not in seen_ids:
                        seen_ids.add(email_id)
                        email_queue.put(email_id)


def main():
    print("Starting initial email fetch...")
    initial_ids = get_recent_unprocessed_emails()
    print(f"Queuing {len(initial_ids)} unprocessed recent emails...")

    with seen_lock:
        for eid in initial_ids:
            seen_ids.add(eid)
            email_queue.put(eid)

    # Start background threads
    threading.Thread(target=email_worker, daemon=True).start()
    threading.Thread(target=change_listener, daemon=True).start()

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("Shutting down...")


if __name__ == "__main__":
    main()