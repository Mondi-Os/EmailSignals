from clientRequests.VFModelsRequest import *
from datetime import datetime, timedelta

# 1. create a new collection that the question goes in --> Done
# 2. watch this collection. once the collection is 'changed' retrieve the unprocessed question(s) --> Done
#TODO
# 3. read the [result][solutions] along with the [email info] for each question (depending on how it is structure)
# 4. pass as 'context' to the llm the solutions from the 'result_collection' and as a 'question' the question from step 3
# 5. return/write a structured answer to the collection from step 2 - this has to be a new record


# question = "What is happening with Trump and Jerome Powell? Explain Briefly"
#
# test =run_llm_query(question, context_text=None)
# print(test["response"]["output"]["message"]["content"][0]["json"]["solutions"])


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


# Aggregation pipeline
pipeline = [
    {
        "$match": {
            "email_info.date": {"$gte": datetime.now() - timedelta(weeks=2)}
        }
    },
    {
        "$project": {
            "_id": 0,
            "email_info": 1,
            "solutions": {
                "$arrayElemAt": [
                    "$response.output.message.content",
                    0
                ]
            }
        }
    },
    {
        "$project": {
            "email_info": 1,
            "solutions": "$solutions.json.solutions"
        }
    }
]

# Run the aggregation
results = list(result_collection.aggregate(pipeline))

# Print or process results
for doc in results:
    print(doc)