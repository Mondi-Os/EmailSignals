import vip
from vip.vip_excepts import ModelAccessError,TokenLimitError, NetworkError, APIError
import json
from vfcfg import *

def run_llm_query(question: str, model_name: str):
    try:
        client = vip.VIPClient(
            api_key="498c67ab-1003-4f24-b07a-85e54cd202ac",  # Replace this securely in prod
            user_name=USER,
            vftoken=TOKEN,
            env='prd'
        )

        print(f"Querying model [{model_name}] with question: \n{question}")
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": question}],
            response_format=expected_schema,
            max_tokens=32768,
            temperature=0
        )

        return json.dumps(response["output"]["message"]["content"], indent=2)

    except ModelAccessError as e:
        return {"error": f"Model access denied. Details: {e.message}"}
    except TokenLimitError as e:
        return {"error": f"Token limit error. Details: {e.message}"}
    except NetworkError as e:
        return {"error": f"Connection or timeout error. Details: {e.message}"}
    except APIError as e:
        return {"error": f"API error: {e.status_code} - {e.message}"}
    except RuntimeError as e:
        return {"error": f"Runtime error. Details: {e}"}
    except ValueError as e:
        return {"error": f"Invalid API key format. Details: {e}"}


result = run_llm_query(
    question="What are the top solutions to reduce market volatility?",
    model_name="valt-chat-rr-deepseek-r1-full-aws"
)

print(result)