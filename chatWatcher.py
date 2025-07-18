from clientRequests.VFModelsRequest import *
from datetime import datetime, timedelta

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


def fetch_results_with_solutions(filter_dict={}, limit=1):
    """Fetch email_info and extract solutions from the result collection. Used for the chat functionality"""

    documents = result_collection.find(filter_dict, {
        "email_info": 1,
        "questions.response.output.message.content": 1
        }).sort("_id", -1).limit(limit)
    cleaned_results = []
    for doc in documents:
        email_info = doc.get("email_info", {})
        questions = doc.get("questions", [])
        extracted_solutions = []
        for q in questions:
            if q:
                solutions = q["response"]["output"]["message"]["content"]["solutions"]
                if solutions[0]["solution"] not in ["Yes", "No"]: # Only processed questions and not single word answers
                    try:
                        sol = [sol['solution'] for sol in solutions]
                        extracted_solutions.append(sol)
                    except (KeyError, IndexError, TypeError) as e:
                        print(f"{q}  -----  \033[1;31mError to retrieve question {e}\033[0m")
                        continue

        cleaned_results.append({
            "email_info": email_info,
            "solutions": extracted_solutions
        })

    return cleaned_results


results = fetch_results_with_solutions(filter_dict={}, limit=1)
print(results)