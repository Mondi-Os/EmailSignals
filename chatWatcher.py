from clientRequests.VFModelsRequest import *
from datetime import datetime, timedelta
import json, os

# 1. create a new collection that the question goes in --> Done
# 2. watch this collection. once the collection is 'changed' retrieve the unprocessed question(s) --> Done
#TODO
# 3. read the [result][solutions] along with the [email info] for each question (depending on how it is structure)
# 4. pass as 'context' to the llm the solutions from the 'result_collection' and as a 'question' the question from step 3
# 5. return/write a structured answer to the collection from step 2 - this has to be a new record


def chat_listener():
    """Listens for new inserts in the 'chat' collection and prints a message."""

    chat_collection = db["chat"]

    with chat_collection.watch(full_document="updateLookup") as stream:
        print("Listening for new inserts in the 'chat' collection...\n")
        for change in stream:
            if change.get("operationType") == "insert":
                chat_id = change["documentKey"]["_id"]
                full_doc = change.get("fullDocument", {})
                print(f"New chat message inserted: _id={chat_id}, from={full_doc['question_from']}, question={full_doc['question']}")


def fetch_results_with_solutions(filter_dict={}, limit=1, question_id_prefixes=None):
    """
    Fetch structured results for each email:
    - email_info: full document
    - processed_info: full document
    - questions: only question_id, question_parent_id, question, and solutions[]
    Supports filtering by question_id prefixes.
    """
    documents = result_collection.find(filter_dict, {
        "email_info": 1,
        "processed_info": 1,
        "questions.question_id": 1,
        "questions.question_parent_id": 1,
        "questions.question": 1,
        "questions.response.output.message.content": 1,
        "questions.processed": 1
    }).sort("_id", -1).limit(limit)

    results = []
    total_questions_considered = 0

    for doc in documents:
        email_info = doc.get("email_info", {})
        processed_info = doc.get("processed_info", {})
        questions = doc.get("questions", [])

        simplified_questions = []

        for q in questions:
            if not q or not q.get("processed", False):
                continue

            qid = q.get("question_id", "")
            if question_id_prefixes and not any(qid.startswith(prefix) for prefix in question_id_prefixes):
                continue

            total_questions_considered += 1

            # Extract content safely
            content = q.get("response", {}).get("output", {}).get("message", {}).get("content")
            solutions = []

            if isinstance(content, dict):
                solutions = content.get("solutions", [])
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if "solutions" in item:
                            solutions = item["solutions"]
                            break
                        elif "json" in item and "solutions" in item["json"]:
                            solutions = item["json"]["solutions"]
                            break
                        elif "solution" in item:
                            solutions = [{"solution": item["solution"]}]
                            break

            simplified_questions.append({
                "question_id": q.get("question_id"),
                "question_parent_id": q.get("question_parent_id"),
                "question": q.get("question"),
                "solutions": [s["solution"] for s in solutions if "solution" in s]
            })

        results.append({
            "email_info": email_info,
            "processed_info": processed_info,
            "questions": simplified_questions
        })

    print(f"\nTotal questions considered (processed and matched prefix): {total_questions_considered}\n")

    return results


#TODO structure the tree better so it has less duplicate questions
results = fetch_results_with_solutions(filter_dict={}, limit=135, question_id_prefixes=["2_203_200301", "2_203_200302", "2_203_200303", "2_203_200304"])

# for i in results:
#     print(i)
# print(results)

# start = datetime.now()
# print(start)
#
question = (
    "Based on the provided trading-related emails, identify the top 3 most frequently suggested trades from the past week. "
    "Return the output as a JSON object under the key 'solutions'. Each solution should include: "
    "'Signal - Product - Times suggested'. Additionally, for each solution, provide a 'times_suggested' count and a list of its occurrences, "
    "with the following fields for each occurrence: email_id, date, from, author, and institution."
)
#
# llm_test = run_llm_query(question=question, context_text=str(results))
#
# end = datetime.now()
# print("Process too: ", end - start)
#
#
# output_path = os.path.join(os.getcwd(), "llm_test_output.json")
# # Write to file
# with open(output_path, "w", encoding="utf-8") as f:
#     json.dump(llm_test, f, indent=2, ensure_ascii=False)