import vip
from vip.vip_excepts import ModelAccessError,TokenLimitError, NetworkError, APIError
import json
from vfcfg import *

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

            raw_content = response["output"]["message"]["content"]

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



# Call the run_llm_queries()
context = "The latest CPI data released this morning showed that U.S. inflation cooled more than expected in June. Headline CPI rose just 0.1% month-over-month, bringing the year-over-year rate down to 3.1% — lower than consensus expectations of 3.3%. Core CPI, which excludes food and energy, also decelerated to 3.5%, down from 3.7% last month. The decline in inflation was driven by softening shelter costs, a continued drop in used car prices, and stabilization in energy prices. Market participants interpreted the print as a dovish surprise, leading to a swift repricing of rate expectations. Fed Funds futures now imply just a 10% chance of a further hike in the September meeting and nearly 100bps of cuts priced in over the next 12 months. Risk assets rallied sharply following the release. The S&P 500 rose 1.4%, while the Nasdaq gained 2.2% as bond yields declined across the curve. The U.S. 10-year Treasury yield fell by 11bps to 3.92%, and the 2-year dropped 15bps to 4.16%. The dollar weakened against major peers, particularly the euro and yen, as rate differentials narrowed. Equity sectors sensitive to interest rates — such as tech and real estate — outperformed. REITs posted a 3.1% gain on the session. Meanwhile, gold saw renewed interest, rallying to $2,010/oz as real yields declined. Strategically, the CPI surprise bolsters the case for duration exposure and calls for reassessing short USD positions. Traders with macro exposure are now favoring long equities and steepeners in rates, particularly 2s10s. Volatility is expected to stay elevated over the next week as markets digest the implications for the Fed's trajectory and upcoming earnings season. Stay tuned for Powell’s remarks at Jackson Hole next week, which could further clarify the Fed’s policy stance."
questions = [
    "Is this a macro event? If so, what is the specific event?",
    "Is there a trading signal in the email? If so, what is the suggested trade or signal?",
    "Does this email imply any change in monetary policy expectations? If so, what change?"
]
responses = run_llm_queries(questions, context_text=context)
print(json.dumps(responses, indent=2))