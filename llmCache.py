import hashlib
from clientRequests.mongoRequests import *
from bson import ObjectId
import os

def list_json_files(folder_path="C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/review_results/"):
    """Return a list of full paths to all .json files in the specified folder."""
    json_paths = [
        os.path.join(folder_path, filename)
        for filename in os.listdir(folder_path)
        if filename.endswith(".json")
        ]
    return json_paths


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


def add_hash_to_questions(json_paths):
    """
    Add a hash to each question in the JSON file based on:
    - the question text
    - the email body retrieved via fetch_emails_from_database()
    """
    for path in json_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            email_info = data.get("email_info", {})
            email_id = email_info.get("_id", "").strip().lower()

            # Fetch body from DB using your standard function
            result = fetch_emails_from_database(
                filter_dict={"_id": ObjectId(email_id)},
                limit=1
            )

            if not result:
                print(f"No email found in DB for: {email_id}")
                continue

            email_body = result[0].get("body", "").strip().lower()
            questions = data.get("questions", [])
            modified = False

            for q in questions:
                question_text = q.get("question", "").strip().lower()
                hash_input = f"{question_text}|{email_body}"
                q_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

                if q.get("hash") != q_hash:
                    q["hash"] = q_hash
                    modified = True

            if modified:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"Updated question hashes in: {os.path.basename(path)}")
            else:
                print(f"No changes needed for: {os.path.basename(path)}")

        except Exception as e:
            print(f"Failed to process {path}: {e}")


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
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db[collection_llm_cache]

    # Step 1: Compute all question hashes for this email
    hash_to_question = {}
    for q in questions:
        h = compute_question_hash(q, email_body)
        hash_to_question[h] = q

    all_hashes = list(hash_to_question.keys())

    # Step 2: Query DB for matching hashes
    db_records = list(collection.find({ "hash": { "$in": all_hashes } }))

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