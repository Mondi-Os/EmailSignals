import vip
from vip.vip_excepts import ModelAccessError,TokenLimitError, NetworkError, APIError
from clientRequests.mongoRequests import *
from credentials.llmSchema import *

def run_llm_queries(questions, model_name: str="valt-chat-rr-deepseek-r1-full-aws", context_text: str = None):
    """
    Run queries against a specified LLM model using the VIPClient.

    :param questions: A list of a question(s).
    :param model_name: Options: valt-chat-rr-deepseek-r1-full-aws, valt-chat-rr-llama-3-70b-aws, valt-chat-rr-anthropic-3-7-aws
    :param context_text: Email (or other text)
    :return: A list of dictionaries with question and response pairs.
    """

    # Normalize to list if single question
    if isinstance(questions, str):
        questions = [questions]

    try:
        client = vip.VIPClient(
            api_key="498c67ab-1003-4f24-b07a-85e54cd202ac", #TODO Replace this securely in prod
            user_name=USER,
            vftoken=TOKEN,
            env='prd'
        )

        results = []

        for question in questions:
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

            results.append({
                "question": question,
                "response": output
            })

        return results

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