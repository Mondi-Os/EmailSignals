from clientRequests.VFModelsRequest import *
from datetime import datetime
import os
import json
import sys


class LLMPipeline:
    def __init__(self):
        with open("framework/promptsFrameworkLayer1.json") as f:
            self.layer1 = json.load(f)
        with open("framework/promptsFrameworkLayer2.json") as f:
            self.layer2 = json.load(f)
        with open("framework/promptsFrameworkLayer3.json") as f:
            self.layer3 = json.load(f)
        # with open("framework/test1.json") as f:
        #     self.layer1 = json.load(f)
        # with open("framework/test2.json") as f:
        #     self.layer2 = json.load(f)
        # with open("framework/test3.json") as f:
        #     self.layer3 = json.load(f)

    def run_batch(self, email_docs):
        """
        Run LLM pipeline for multiple emails (parsed_docs), save each email separately.
        """
        start_time = datetime.now()
        print(f"Pipeline started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        output_dir = "review_results"
        os.makedirs(output_dir, exist_ok=True)

        for email in email_docs:
            email_id = str(email["_id"])
            context = str(email["body"])
            print(f"Processing email ID: {email_id}")

            output = self.run_single(email_id, context)

            # Combine all questions with a 'layer' label
            all_questions = []

            for q in output.get("main", []):
                q_copy = q.copy()
                q_copy["layer"] = 1
                all_questions.append(q_copy)

            for q in output.get("sub", []):
                q_copy = q.copy()
                q_copy["layer"] = 2
                all_questions.append(q_copy)

            for q in output.get("subsub", []):
                q_copy = q.copy()
                q_copy["layer"] = 3
                all_questions.append(q_copy)

            # Final result format
            email_result = {
                "email_info": {
                    "_id": email_id,
                    "date": email.get("date"),
                    "from": email.get("from")
                },
                "questions": all_questions
            }

            # Save per-email result
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{timestamp}--{email_id}.json"
            output_path = os.path.join(output_dir, filename)

            #TODO Here to plug the MongoDB upsert code instead of saving to JSON files
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(email_result, f, indent=2, ensure_ascii=False)

        end_time = datetime.now()
        print(f"Pipeline finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total duration: {end_time - start_time}")

    def run_single(self, email_id, context):
        """
        Run LLM pipeline for a single email body.
        """

        # ========= Layer 1 =========
        main_question_texts = [q["question"] for q in self.layer1]
        main_responses = run_llm_queries(main_question_texts, context_text=context)

        results = []
        main_answer_map = {}
        for i, response in enumerate(main_responses):
            question = self.layer1[i]
            answer = response["response"]["output"]["message"]["content"]
            answer_text = answer[0].get("text", "").strip().lower() if isinstance(answer, list) else str(
                answer).strip().lower()
            main_answer_map[question["question_id"]] = answer_text

            enriched = {
                "question_id": question["question_id"],
                "ref": question["ref"],
                "question": question["question"],
                "email_id": email_id,
                "response": response,
                "processed": True
            }
            results.append(enriched)

        # ========= Layer 2 =========
        sub_results = []
        subq_to_ask = [q for q in self.layer2 if main_answer_map.get(q["question_parent_id"]) == "yes"]
        sub_question_texts = [q["question"] for q in subq_to_ask]
        sub_responses = run_llm_queries(sub_question_texts, context_text=context)

        # Answered questions in layer 2
        sub_answer_map = {}
        answered_ids = set()
        for i, response in enumerate(sub_responses):
            q_meta = subq_to_ask[i]
            answer = response["response"]["output"]["message"]["content"]
            answer_text = answer[0].get("text", "").strip().lower() if isinstance(answer, list) else str(
                answer).strip().lower()
            sub_answer_map[q_meta["question_id"]] = answer_text

            enriched = {
                "question_id": q_meta.get("id") or q_meta.get("question_id"),
                "parent_id": q_meta.get("parent_id") or q_meta.get("question_parent_id"),
                "ref": q_meta["ref"],
                "question": q_meta["question"],
                "email_id": email_id,
                "response": response,
                "processed": True
            }
            sub_results.append(enriched)
            answered_ids.add(q_meta["question_id"])

        # Ananswered question in layer 2
        for q in self.layer2:
            if q["question_id"] not in answered_ids:
                sub_results.append({
                    "question_id": q["question_id"],
                    "parent_id": q.get("question_parent_id"),
                    "ref": q["ref"],
                    "question": q["question"],
                    "email_id": email_id,
                    "processed": False
                })

        # ========= Layer 3 =========
        subsub_results = []
        subsub_to_ask = [
            q for q in self.layer3
            if sub_answer_map.get(q["question_parent_id"]) == q.get("parent_answer", "").strip().lower()
            ]

        for q in subsub_to_ask:
            q["email_id"] = email_id

        subsub_question_texts = [q["question"] for q in subsub_to_ask]
        print(f"subsub_question_texts: {subsub_question_texts}")  # TODO remove (debug print)

        subsub_responses = run_llm_queries(subsub_question_texts, context_text=context)
        print(f"subsub_responses: {subsub_responses}") #TODO remove (debug print)

        # Answered questions in layer 3
        subsub_answered_ids = set()
        for i, response in enumerate(subsub_responses):
            q_meta = subsub_to_ask[i]
            print(f"response:    {response}") #TODO remove (debug print)
            enriched = {
                "question_id": q_meta.get("id") or q_meta.get("question_id"),
                "parent_id": q_meta.get("parent_id") or q_meta.get("question_parent_id"),
                "ref": q_meta["ref"],
                "question": q_meta["question"],
                "email_id": email_id,
                "response": response["response"],
                "processed": True
            }
            subsub_results.append(enriched)
            subsub_answered_ids.add(q_meta["question_id"])

        # Ananswered question in layer 3
        for q in self.layer3:
            if q["question_id"] not in subsub_answered_ids:
                subsub_results.append({
                    "question_id": q["question_id"],
                    "parent_id": q.get("question_parent_id"),
                    "ref": q["ref"],
                    "question": q["question"],
                    "email_id": email_id,
                    "processed": False
                })

        # ======== Clean responses =========
        self.clean_response_fields(results)
        self.clean_response_fields(sub_results)
        self.clean_response_fields(subsub_results)

        return {
            "email_id": email_id,
            "main": results,
            "sub": sub_results,
            "subsub": subsub_results
        }

    @staticmethod
    def clean_response_fields(data_section):
        for item in data_section:
            response = item.get("response", {})
            if isinstance(response, dict):
                response.pop("stop_reason", None)
                response.pop("usage", None)

pipeline = LLMPipeline()
pipeline.run_batch(email_info)