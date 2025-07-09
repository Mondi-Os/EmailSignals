import os
from clientRequests.VFModelsRequest import *
from datetime import datetime

class LLMPipeline:
    def __init__(self, email_context):
        self.email_context = email_context
        with open("framework/promptsFrameworkMain.json") as f:
            self.main_questions = json.load(f)
        with open("framework/promptsFrameworkBranches.json") as f:
            self.sub_questions = json.load(f)

    def run(self):
        main_question_texts = [q["question"] for q in self.main_questions]
        main_responses = run_llm_queries(main_question_texts, context_text=str(self.email_context))

        results = []
        for i, response in enumerate(main_responses):
            enriched = {
                "question_id": self.main_questions[i]["question_id"],
                "ref": self.main_questions[i]["ref"],
                "question": self.main_questions[i]["question"],
                "response": response["response"]
            }
            results.append(enriched)

        subq_to_ask = []
        for result in results:
            answer_content = result["response"]["output"]["message"]["content"]
            answer_text = answer_content[0]["text"].strip().lower() if isinstance(answer_content, list) else str(answer_content).strip().lower()
            if answer_text == "yes":
                matching_subqs = [
                    q for q in self.sub_questions
                    if q.get("parent_id") == result["question_id"] or q.get("question_parent_id") == result["question_id"]
                ]
                subq_to_ask.extend(matching_subqs)

        sub_question_texts = [q["question"] for q in subq_to_ask]
        sub_responses = run_llm_queries(sub_question_texts, context_text=str(self.email_context))

        sub_results = []
        for i, response in enumerate(sub_responses):
            enriched = {
                "question_id": subq_to_ask[i].get("id") or subq_to_ask[i].get("question_id"),
                "parent_id": subq_to_ask[i].get("parent_id") or subq_to_ask[i].get("question_parent_id"),
                "ref": subq_to_ask[i]["ref"],
                "question": subq_to_ask[i]["question"],
                "response": response["response"]
            }
            sub_results.append(enriched)

        final_output = {
            "main": results,
            "sub": sub_results
        }

        self.clean_response_fields(final_output.get("main", []))
        self.clean_response_fields(final_output.get("sub", []))

        output_dir = "review_results"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}___llm_results.json"
        output_path = os.path.join(output_dir, filename)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)

    @staticmethod
    def clean_response_fields(data_section):
        """
        Remove specific fields from the response json.
        """
        for item in data_section:
            response = item.get("response", {})
            if isinstance(response, dict):
                response.pop("stop_reason", None)
                response.pop("usage", None)

pipeline = LLMPipeline(email_body)
pipeline.run()