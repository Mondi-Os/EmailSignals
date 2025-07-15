import re, json


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
    """
    Transforms all responses into a consistent format:
    response["output"]["message"]["content"] = {"solutions": [{"solution": "..."}]}
    """
    updated_questions = []

    for question in email_result_dict["questions"]:
        response = question.get("response", {}).get("response", {})
        output = response.get("output", {})
        message = output.get("message", {})
        content = message.get("content", None)

        if not content:
            updated_questions.append(question)
            continue

        normalized = None

        if isinstance(content, dict):
            # Already normalized?
            if "solutions" in content:
                normalized = content
            elif "json" in content and "solutions" in content["json"]:
                normalized = content["json"]

        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if "text" in item:
                        normalized = {
                            "solutions": [{"solution": item["text"].strip()}]
                        }
                        break
                    elif "solution" in item:
                        normalized = {
                            "solutions": [{"solution": item["solution"].strip()}]
                        }
                        break
                    elif "json" in item and "solutions" in item["json"]:
                        normalized = item["json"]
                        break

        # Apply normalized structure if valid
        if normalized:
            email_result_dict["questions"][email_result_dict["questions"].index(question)]["response"]["response"]["output"]["message"]["content"] = normalized

        updated_questions.append(question)

    return {
        "email_info": email_result_dict["email_info"],
        "questions": updated_questions
    }



def layer_preprocessing(layer: int, question, email_id, response=None, processed=True):
    """Used within the run_single() method to modify/enrich the dict/json format."""
    enriched = {
        "question_id": question["question_id"],
        "parent_id": question["question_parent_id"],
        "ref": question["ref"],
        "question": question["question"],
        "email_id": email_id,
        "processed": processed,
        "layer": question.get("layer", layer)
    }

    if processed:
        enriched["response"] = response

    return enriched