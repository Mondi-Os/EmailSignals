import hashlib
from clientRequests.mongoRequests import *
from bson import ObjectId


def load_all_questions_from_json_files(layer1_path, layer2_path, layer3_path):
    """Loads all question dictionaries from the three JSON prompt files (layer 1, 2, 3)."""
    all_questions = []

    # Layer 1
    with open(layer1_path, "r", encoding="utf-8") as f:
        layer1 = json.load(f)
        for q in layer1:
            q["layer"] = 1
            all_questions.append(q)

    # Layer 2
    with open(layer2_path, "r", encoding="utf-8") as f:
        layer2 = json.load(f)
        for q in layer2:
            q["layer"] = 2
            all_questions.append(q)

    # Layer 3
    with open(layer3_path, "r", encoding="utf-8") as f:
        layer3 = json.load(f)
        for q in layer3:
            q["layer"] = 3
            all_questions.append(q)

    return all_questions


def process_questions_and_upsert(email_result_dicts):
    """
    Process email result dicts:
    - Compute question hash using question + email body
    - Keep only: hash, emailBody, question, response
    - Save results in a dictionary keyed by email_id
    - Upsert each record into the llm_cache collection using the hash
    """
    for record in email_result_dicts:
        try:
            email_info = record.get("email_info", {})
            questions = record.get("questions", [])

            email_id = email_info.get("_id", "").strip().lower()
            if not email_id:
                print("Missing email ID.")
                continue

            email_result = fetch_emails_from_database(
                filter_dict={"_id": ObjectId(email_id)},
                limit=1
            )

            if not email_result:
                print(f"No email found in DB for: {email_id}")
                continue

            email_body = email_result[0].get("body", "").strip().lower()

            for q in questions:
                question_text = q.get("question", "").strip().lower()

                # Compute hash
                hash_input = f"{question_text}|{email_body}"
                q_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

                # Add the hash to the question object
                q_with_hash = q.copy()
                q_with_hash["hash"] = q_hash
                q_with_hash["emailBody"] = email_body  # Optionally add context to cache for visibility

                # Upsert the entire question record into cache
                cache_collection.update_one(
                    {"hash": q_hash},
                    {"$set": q_with_hash},
                    upsert=True
                )

        except Exception as e:
            print(f"Failed to process record: {e}")
    print("All questions processed and upserted into the cache collection.")
    pass


def compute_question_hash(question, email_body):
    """Compute a hash from the question text and email body. Must match how `add_hash_to_questions()` generates it."""
    question_text = question.get("question", "").strip().lower()
    body = email_body.strip().lower()
    hash_input = f"{question_text}|{body}"
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


def llm_simulation(questions, email_body):
    """
    Simulates LLM logic by checking if all question hashes (based on question + email_body)
    exist in the MongoDB 'cache_llm' collection.

    If ALL exist: returns structured result.
    If ANY are missing: returns None (LLM should run).
    """

    # Step 1: Compute all question hashes for this email
    hash_to_question = {}
    for q in questions:
        h = compute_question_hash(q, email_body)
        hash_to_question[h] = q

    all_hashes = list(hash_to_question.keys())

    # Step 2: Query DB for matching hashes
    db_records = list(cache_collection.find({ "hash": { "$in": all_hashes } }))

    # Step 3: Validate if ALL required hashes are found
    found_hashes = {doc["hash"] for doc in db_records}
    missing = [h for h in all_hashes if h not in found_hashes]

    if missing:
        print(f"Missing {len(missing)} hash(es). Triggering LLM.")
        return None  # Trigger LLM

    if not db_records:
        print("No matching question hashes found in DB — triggering LLM.")
        return None

    # Step 4: Assemble output structure
    print(db_records)
    response = {
        "questions": []
    }

    for h in all_hashes:
        matched_doc = next((doc for doc in db_records if doc["hash"] == h), None)
        orig_q = hash_to_question.get(h, {})

        if matched_doc:
            answer = matched_doc.get("answer", "")
            layer = orig_q.get("layer")
            processed = bool(answer and str(answer).strip())

            response["questions"].append({
                "hash": h,
                "question": matched_doc.get("question"),
                "answer": matched_doc.get("answer"),
                "question_id": orig_q.get("question_id") or orig_q.get("id"),
                "parent_id": orig_q.get("parent_id") or orig_q.get("question_parent_id"),
                "layer": layer,
                "processed": processed #TODO to be tested
            })
        else:
            print("Not Matched Docs")

    print(f"Cache hit for all {len(all_hashes)} questions.")
    return response

## 1st step before inserting into MongoDB
# add_hash_to_questions(list_json_files())

## 2nd step: Upsert collection
# upsert_into_mongo_based_on_question_hashes(collection_llm_cache, list_json_files())

## 3rd step: Read collection
# print(f"length: {len(read_collection(collection_llm_cache))}")

def process_questions_to_cache(email_result_dicts):
    if isinstance(email_result_dicts, dict):
        email_result_dicts = [email_result_dicts]

    for record in email_result_dicts:
        try:
            email_info = record.get("email_info", {})
            questions = record.get("questions", [])
            email_id = email_info.get("_id", "").strip().lower()

            if not email_id:
                print("Missing email ID.")
                continue

            email_result = fetch_emails_from_database(
                filter_dict={"_id": ObjectId(email_id)},
                limit=1
            )
            if not email_result:
                print(f"No email found in DB for: {email_id}")
                continue

            email_body = email_result[0].get("body", "").strip().lower()

            for q in questions:
                question_text = q.get("question", "").strip().lower()
                q_hash = hashlib.sha256(f"{question_text}|{email_body}".encode("utf-8")).hexdigest()

                flat = {
                    "question_id": q.get("question_id"),
                    "ref": q.get("ref"),
                    "question": q.get("question"),
                    "email_id": email_id,
                    "response": q.get("response"),
                    "processed": q.get("processed"),
                    "layer": q.get("layer"),
                    "hash": q_hash,
                    "emailBody": email_body
                }

                # Upsert into llm_collection
                cache_collection.update_one(
                    {"hash": q_hash},
                    {"$set": flat},
                    upsert=True
                )

        except Exception as e:
            print(f"Failed to process record: {e}")

    print("All questions processed and upserted to llm_collection.")
    pass