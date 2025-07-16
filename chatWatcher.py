from clientRequests.VFModelsRequest import *

#TODO
# 1. create a new collection that the question goes in --> Done
# 2. watch this collection. once the collection is 'changed' retrieve the unprocessed question(s)
# 3. read the [result][solutions] along with the [email info] for each question (depending on how it is structure)
# 4. pass as 'context' to the llm the solutions from the 'result_collection' and as a 'question' the question from step 3
# 5. return/write a structured answer to the collection from step 2 - this has to be a new record


# question = "What is happening with Trump and Jerome Powell? Explain Briefly"
#
# test =run_llm_query(question, context_text=None)
# print(test["response"]["output"]["message"]["content"][0]["json"]["solutions"])