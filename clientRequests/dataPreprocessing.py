import re,hashlib


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

    for question in email_result_dict.get("questions", []):
        response = question.get("response", {})
        output = response.get("output", {})
        message = output.get("message", {})
        content = message.get("content", None)

        if not content:
            updated_questions.append(question)
            continue

        normalized = None

        if isinstance(content, dict):
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
            # Overwrite the content in-place
            question["response"]["output"]["message"]["content"] = normalized

        updated_questions.append(question)

    return {
        "email_info": email_result_dict.get("email_info", {}),
        "questions": updated_questions
    }


def layer_preprocessing(layer: int, question, email_id, response=None, processed=True):
    """Used within the run_single() method to modify/enrich the dict/json format."""
    enriched = {
        "question_id": question["question_id"],
        "parent_id": question["question_parent_id"],
        "ref": question["ref"],
        "question": question["question"],
        "processed": processed,
        "layer": question.get("layer", layer)
    }

    if processed:
        enriched["response"] = response

    return enriched


def compute_question_hash(question, email_body):
    """Compute a hash from the question text and email body."""
    if isinstance(question, dict):
        question_text = question.get("question", "")
    else:
        question_text = str(question)

    body = email_body.strip().lower()
    hash_input = f"{question_text.strip().lower()}|{body}"
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


def extract_answer_text(answer):
    """Extracts the 'solution' string from an LLM response content."""
    if isinstance(answer, list) and answer and "json" in answer[0]:
        if "solutions" in answer[0]["json"]:
            return answer[0]["json"]["solutions"][0]["solution"].strip().lower()
        elif "answer" in answer[0]["json"]:
            return str(answer[0]["json"]["answer"]).strip().lower()

    elif isinstance(answer, list) and answer:
        return (answer[0]["text"] if "text" in answer[0] else answer[0]["solution"]).strip().lower()

    elif isinstance(answer, dict) and "solutions" in answer:
        return answer["solutions"][0]["solution"].strip().lower()

    else:
        return str(answer).strip().lower()



def get_unprocessed(layer_questions, processed_results):
    processed_ids = {q["question_id"] for q in processed_results}
    return [q for q in layer_questions if q["question_id"] not in processed_ids]
