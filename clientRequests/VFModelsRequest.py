import vip
from vip.vip_excepts import ModelAccessError,TokenLimitError, NetworkError, APIError
import json
from credentials.llmSchema import *
from llm_helpers.dataPreprocessing import *

def run_llm_query(question, context_text, model_name: str="valt-chat-rr-deepseek-r1-full-aws"):
    """
    Run queries against a specified LLM model using the VIPClient.

    :param questions: A list of a question(s).
    :param model_name: Options: valt-chat-rr-deepseek-r1-full-aws, valt-chat-rr-llama-3-70b-aws, valt-chat-rr-anthropic-3-7-aws
    :param context_text: Email (or other text)
    :return: A list of dictionaries with question and response pairs.
    """
    try:
        client = vip.VIPClient(
            api_key="498c67ab-1003-4f24-b07a-85e54cd202ac",
            user_name=USER,
            vftoken=TOKEN,
            env='prd'
        )

        if context_text:
            prompt = f"Context:\n{context_text}\n\nQuestion: {question}"
        else:
            prompt = question

        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format=expected_schema,
            max_tokens=32768,
            temperature=0
        )

        raw_content = response

        try:
            # Try to parse if it's a valid JSON string
            parsed_content = json.loads(raw_content)
            output = parsed_content  # already a Python object
        except (TypeError, json.JSONDecodeError):
            output = raw_content  # leave as-is if it's not JSON

        return {
            "question": question,
            "response": output
        }

    # Catch specific exceptions and return error messages
    except ModelAccessError as e:
        return [{"error": f"Model access denied. Details: {e.message}"}]
    except TokenLimitError as e:
        return [{"error": f"Token limit error. Details: {e.message}"}]
    except NetworkError as e:
        return [{"error": f"Connection or timeout error. Details: {e.message}"}]
    except APIError as e:
        return [{"error": f"API error: {e.status_code} - {e.message}"}]
    except RuntimeError as e:
        return [{"error": f"Runtime error. Details: {e}"}]
    except ValueError as e:
        return [{"error": f"Invalid API key format. Details: {e}"}]


def cache_or_llm(question,  context_text, model_name: str="valt-chat-rr-deepseek-r1-full-aws"):
    """Check if question exists in the 'llm_cache' collection. If so, retrieve the data from the collection otherwise run the run_llm_query"""
    # Compute hash based on (question + email body)
    q_hash = compute_question_hash(question, context_text)
    # Search in the 'llm_cache' collection for the hash
    cache_collection = db["llm_cache"]  # Collection: LLM cache results
    cached_doc = cache_collection.find_one({"hash": q_hash})

    if cached_doc: # if hash exists in the 'llm_cache'
        llm_result = {
            "question": cached_doc["question"],
            "response": cached_doc["response"],
            "from_cache": True
        }
        # print("Cached:   ", extract_answer_text(llm_result["response"]["output"]["message"]["content"])) #TODO remove debugging
        answer_text = extract_answer_text(llm_result["response"]["output"]["message"]["content"])
        return llm_result, answer_text

    else: # if hash does not exist in the 'llm_cache'
        result = run_llm_query(question, context_text, model_name)
        # print("New LLM Query:    ", question) #TODO remove debugging
        # print("Result:    ", result)  # TODO remove debugging
        cache_collection.update_one(
            {"hash": q_hash},
            {"$set": {
                "hash": q_hash,
                "question": question["question"],
                "body": context_text,
                "response": result["response"]
                } },
            upsert=True
        )

        llm_result = {
            "question": result["question"],
            "response": result["response"],
            "from_cache": False
        }
        answer_text = extract_answer_text(llm_result["response"]["output"]["message"]["content"])
        return llm_result, answer_text