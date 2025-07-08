import vip
from vip.vip_excepts import ModelAccessError,TokenLimitError, NetworkError, APIError
import json
import vfcfg

expected_schema = {
    "name": "test_schema",
    "description": "Top solutions (1-5 items allowed)",
    "parameters": {
        "type": "object",
        "properties": {
            "solutions": {
                "type": "array",
                "description": "List of top solutions, up to 5 items",
                "minItems": 1,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "solution": {"type": "string"},
                        "method": {
                            "type": "string",
                            "description": "Optional methodology used"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Optional rationale for this solution"
                        }
                    },
                    "required": ["solution"],
                }
            }
        },
        "required": ["solutions"],
    }
}

try:

    client = vip.VIPClient(

        api_key="498c67ab-1003-4f24-b07a-85e54cd202ac", # Philipp project Key (You and Bobby are in the list, the US team will add Mondi after they get in)

        user_name=vfcfg.USER,

        vftoken=vfcfg.TOKEN,

        env = 'prd'

    )

    # valt-chat-rr-deepseek-r1-full-aws       valt-chat-rr-llama-3-70b-aws      valt-chat-rr-anthropic-3-7-aws

    print ("About to call the model ..")
    response = client.chat.completions.create(
        model="valt-chat-rr-anthropic-3-7-aws",
        messages=[{"role": "user", "content": "What is a Bermudan Callable Range Accrual Swaption"}],
        response_format=expected_schema,
        max_tokens=32768,
        temperature = 0
    )

    print(json.dumps(response, indent=2))

except ModelAccessError as e:
    print(f"Model access denied. Details: {e.message}")
except TokenLimitError as e:
    print(f"Token limit error. Details: {e.message}")
except NetworkError as e:
    print(f"connection or timeout error. Details: {e.message}")  # Added NetworkError
except APIError as e:
    print(f"API error: {e.status_code} - {e.message}")
except RuntimeError as e:
    print(f"Report invalid response. Details: {e}")
except ValueError as e:
    print(f"API key format is invalid. Details: {e}")