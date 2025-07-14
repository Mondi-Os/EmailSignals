import re, json
from copy import deepcopy


def clean_email_body(text: str) -> str:
    if not text:
        return ""

    lower_text = text.lower()
    unsubscribe_index = lower_text.find("unsubscribe")
    if unsubscribe_index != -1:
        text = text[:unsubscribe_index]

    #TODO if more data preprocessing could be added would be great for data dimensionality/run time

    # Remove specific patterns and unwanted characters
    text = text.replace('\xa0', ' ')
    text = text.replace('-----------------------------------------------------------------------------', '-')
    text = text.replace('This Message originated outside your organization.', ' ')
    text = text.replace('\r', ' ')  # Handle carriage returns
    text = text.replace('\n', ' ')  # Flatten line breaks

    # Remove multiple spaces and strip edges
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def normalize_solutions_structure(email_result_dict):
    """Transforms all responses into a consistent format with ["solutions"][{"solution": "..."}]"""
    updated_questions = []
    for question in email_result_dict["questions"]:
        response = question.get("response", {}).get("response", {})
        content = response.get("output", {}).get("message", {}).get("content", None)
        if not content:
            updated_questions.append(question)
            continue

        # If content is a list of dicts (e.g. [{"text": "Yes"}]), extract first text and wrap it in target structure
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if "text" in item:
                        text = item["text"].strip()
                        response["output"]["message"]["content"] = {
                            "solutions": [{"solution": text}]
                        }
                        break
                    elif "json" in item and "solutions" in item["json"]:
                        response["output"]["message"]["content"] = item["json"]
                        break
        elif isinstance(content, dict) and "json" in content and "solutions" in content["json"]:
            response["output"]["message"]["content"] = content["json"]

        updated_questions.append(question)

    return {
        "email_info": email_result_dict["email_info"],
        "questions": updated_questions
    }