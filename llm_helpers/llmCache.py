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


def compute_question_hash(question, email_body):
    """Compute a hash from the question text and email body."""
    if isinstance(question, dict):
        question_text = question.get("question", "")
    else:
        question_text = str(question)

    body = email_body.strip().lower()
    hash_input = f"{question_text.strip().lower()}|{body}"
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


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
                    "question_parent_id":q.get("parent_id") or q.get("question_parent_id"),
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
            print(f"Failed to hash record: {e}")
    pass