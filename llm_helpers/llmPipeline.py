from clientRequests.VFModelsRequest import *
from llm_helpers.llmCache import *
from datetime import datetime
import sys

class LLMPipeline:
    def __init__(self):
        with open("C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/framework/promptsFrameworkLayer1.json") as f:
            self.layer1 = json.load(f)
        with open("C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/framework/promptsFrameworkLayer2.json") as f:
            self.layer2 = json.load(f)
        with open("C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/framework/promptsFrameworkLayer3.json") as f:
            self.layer3 = json.load(f)
        # with open("C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/framework/test1.json") as f:
        #     self.layer1 = json.load(f)
        # with open("C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/framework/test2.json") as f:
        #     self.layer2 = json.load(f)
        # with open("C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/framework/test3.json") as f:
        #     self.layer3 = json.load(f)

    def run_batch(self, email_docs):
        """Run LLM pipeline for multiple emails (parsed_docs), save each email separately."""
        start_time = datetime.now()
        print(f"Pipeline started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        for email in email_docs:
            context = str(email["body"])
            email_id = str(email["_id"])
            email_info = {
                "_id": email_id,
                "date": email.get("date"),
                "from": email.get("from")
            }
            print(f"Processing email ID: {email_id}")

            # Execute the run_single() to go through the question layers
            result = self.run_single(email_id, context)
            output_questions = result["main"] + result["sub"] + result["subsub"]
            # Email result solutions
            email_result_dict = {
                "email_info": email_info,
                "questions": output_questions
            }
            # Normalize the structure of solutions
            email_result = normalize_solutions_structure(email_result_dict)

            # Upsert into 'result' collection
            result_collection.update_one({"_id": ObjectId(email_id)}, {"$set": email_result}, upsert=True)
            # Upsert into 'cache' collection
            process_questions_to_cache(email_result_dict)
            print(f"Upserted email_id {email_id} into 'result' collection.")

        end_time = datetime.now()
        print(f"Pipeline finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total duration: {end_time - start_time}\n")

    def run_single(self, email_id, context):
        """Run LLM pipeline for a single email body."""
        hashes_found_1, results, main_answer_map = [], [], {}
        questions_to_query, index_map, main_question_texts = [], {}, []

        # ========= Layer 1 =========
        for i, question in enumerate(self.layer1):


            q_hash = compute_question_hash(question, context)
            cached_doc = cache_collection.find_one({"hash": q_hash})

            if cached_doc:
                hashes_found_1.append(q_hash)
                answer_json = cached_doc["response"]["response"]["output"]["message"]["content"]
                if isinstance(answer_json, list) and answer_json and "json" in answer_json[0]:
                    # Format: [{'json': {'solutions': [{'solution': 'Yes'}]}}]
                    answer_text = answer_json[0]["json"]["solutions"][0]["solution"].strip().lower()
                elif isinstance(answer_json, list) and answer_json:
                    # Format: [{'text': 'Yes'}] or [{'solution': 'Yes'}]
                    answer_text = (answer_json[0]["text"] if "text" in answer_json[0] else answer_json[0][
                        "solution"]).strip().lower()
                elif isinstance(answer_json, dict) and "solutions" in answer_json:
                    # Format: {'solutions': [{'solution': 'Yes'}]}
                    answer_text = answer_json["solutions"][0]["solution"].strip().lower()
                else:
                    # Unexpected fallback
                    answer_text = str(answer_json).strip().lower()

                main_answer_map[question["question_id"]] = answer_text
                enriched = layer_preprocessing(layer=1, question=question, email_id=email_id, response=cached_doc["response"], processed=True)
                results.append(enriched)
            else:
                questions_to_query.append(question["question"])
                index_map[len(main_question_texts)] = i
                main_question_texts.append(question["question"])
        print(f"Layer1 hashes found: {len(hashes_found_1)} out of {len(self.layer1)} || email_id: {email_id}")

        # Run LLM for uncached Layer 1 questions
        if questions_to_query:
            uncached_responses = run_llm_queries(questions_to_query, context_text=context)
            for j, response in enumerate(uncached_responses):
                i = index_map[j]
                question = self.layer1[i]
                answer = response["response"]["output"]["message"]["content"]
                answer_text = (
                    answer[0]["json"]["solutions"][0]["solution"].strip().lower()
                    if isinstance(answer, list) and "json" in answer[0]
                    else (answer[0].get("text") or answer[0].get("solution") or "").strip().lower()
                    if isinstance(answer, list)
                    else str(answer).strip().lower()
                )
                main_answer_map[question["question_id"]] = answer_text
                enriched = layer_preprocessing(layer=1, question=question, email_id=email_id, response=response, processed=True)
                results.append(enriched)

        # ========= Layer 2 =========
        hashes_found_2, sub_results, sub_answer_map, answered_ids = [], [], {}, set()
        subq_to_ask, sub_questions, sub_index_map = [], [], {}

        for i, q in enumerate(self.layer2):
            if main_answer_map.get(q["question_parent_id"]) != "yes":
                continue

            q_hash = compute_question_hash(q, context)
            cached_doc = cache_collection.find_one({"hash": q_hash})
            if cached_doc:
                hashes_found_2.append(q_hash)

            if cached_doc and cached_doc["response"] is not None:
                answer_json = cached_doc["response"]["response"]["output"]["message"]["content"]
                if isinstance(answer_json, list) and answer_json and "json" in answer_json[0]:
                    # Format: [{'json': {'solutions': [{'solution': 'Yes'}]}}]
                    answer_text = answer_json[0]["json"]["solutions"][0]["solution"].strip().lower()
                elif isinstance(answer_json, list) and answer_json:
                    # Format: [{'text': 'Yes'}] or [{'solution': 'Yes'}]
                    answer_text = (answer_json[0]["text"] if "text" in answer_json[0] else answer_json[0][
                        "solution"]).strip().lower()
                elif isinstance(answer_json, dict) and "solutions" in answer_json:
                    # Format: {'solutions': [{'solution': 'Yes'}]}
                    answer_text = answer_json["solutions"][0]["solution"].strip().lower()
                else:
                    # Unexpected fallback
                    answer_text = str(answer_json).strip().lower()

                sub_answer_map[q["question_id"]] = answer_text
                sub_results.append(layer_preprocessing(layer=2, question=q, email_id=email_id, response=cached_doc["response"], processed=True))
                answered_ids.add(q["question_id"])
            else:
                sub_questions.append(q["question"])
                subq_to_ask.append(q)
                sub_index_map[len(sub_questions) - 1] = i
        print(f"Layer2 hashes found: {len(hashes_found_2)} out of {len(self.layer2)}|| email_id: {email_id}")

        # Run LLM for uncached Layer 1 questions
        if sub_questions:
            sub_responses = run_llm_queries(sub_questions, context_text=context)
            for j, response in enumerate(sub_responses):
                q_meta = subq_to_ask[j]
                answer = response["response"]["output"]["message"]["content"]
                answer_text = (
                    (answer[0].get("text") or answer[0].get("solution") or "").strip().lower()
                    if isinstance(answer, list) else str(answer).strip().lower()
                )
                sub_answer_map[q_meta["question_id"]] = answer_text
                sub_results.append(layer_preprocessing(layer=2, question=q_meta, email_id=email_id, response=response, processed=True))
                answered_ids.add(q_meta["question_id"])
        # Unanswered layer 2
        for q in self.layer2:
            if q["question_id"] not in answered_ids:
                sub_results.append(layer_preprocessing(layer=2, question=q, email_id=email_id, processed=False))

        # ========= Layer 3 =========
        hashes_found_3, subsub_results, subsub_answered_ids = [], [], set()
        subsub_to_ask, subsub_questions, subsub_index_map = [], [], {}

        for q in self.layer3:
            if sub_answer_map.get(q["question_parent_id"]) != q.get("parent_answer", "").strip().lower():
                continue

            q_hash = compute_question_hash(q, context)
            cached_doc = cache_collection.find_one({"hash": q_hash})

            if cached_doc:
                hashes_found_3.append(q_hash)
                subsub_results.append(layer_preprocessing(layer=3, question=q, email_id=email_id, response=cached_doc["response"], processed=True))
                subsub_answered_ids.add(q["question_id"])
            else:
                subsub_questions.append(q["question"])
                subsub_to_ask.append(q)
                subsub_index_map[len(subsub_questions) - 1] = q["question_id"]
        print(f"Layer3 hashes found: {len(hashes_found_3)} out of {len(self.layer3)}|| email_id: {email_id}")

        if subsub_questions:
            subsub_responses = run_llm_queries(subsub_questions, context_text=context)
            for i, response in enumerate(subsub_responses):
                q_meta = subsub_to_ask[i]
                subsub_results.append(layer_preprocessing(layer=3, question=q_meta, email_id=email_id, response=response, processed=True))
                subsub_answered_ids.add(q_meta["question_id"])

        for q in self.layer3:
            if q["question_id"] not in subsub_answered_ids:
                subsub_results.append(layer_preprocessing(layer=3, question=q, email_id=email_id, processed=False))

        # ========= Clean up =========
        self.clean_response_fields(results)
        self.clean_response_fields(sub_results)
        self.clean_response_fields(subsub_results)

        return {
            "email_id": email_id,
            "main": results,
            "sub": sub_results,
            "subsub": subsub_results
        }

    # def run_single(self, email_id, context):
    #     """Run LLM pipeline for a single email body."""
    #     # ========= Layer 1 =========
    #     main_question_texts = [q["question"] for q in self.layer1]
    #     main_responses = run_llm_queries(main_question_texts, context_text=context)
    #
    #     results = []
    #     main_answer_map = {}
    #     for i, response in enumerate(main_responses):
    #         question = self.layer1[i]
    #         answer = response["response"]["output"]["message"]["content"]
    #
    #         # Extract answer text based on the response format (sometimes LLM returns "text" and sometimes "solution")
    #         if isinstance(answer, list) and "json" in answer[0]:
    #             answer_text = (
    #                 answer[0]["json"]["solutions"][0]["solution"].strip().lower()
    #                 if answer[0]["json"].get("solutions") else ""
    #             )
    #         else:
    #             answer_text = (
    #                 (answer[0].get("text") or answer[0].get("solution") or "").strip().lower()
    #                 if isinstance(answer, list) else str(answer).strip().lower()
    #             )
    #
    #         main_answer_map[question["question_id"]] = answer_text
    #         enriched = layer_preprocessing(layer=1, question=question, email_id=email_id, response=response,
    #                                        processed=True)
    #         results.append(enriched)
    #
    #     # ========= Layer 2 =========
    #     sub_results = []
    #     subq_to_ask = [q for q in self.layer2 if main_answer_map.get(q["question_parent_id"]) == "yes"]
    #     sub_question_texts = [q["question"] for q in subq_to_ask]
    #     sub_responses = run_llm_queries(sub_question_texts, context_text=context)
    #
    #     # Answered questions in layer 2
    #     sub_answer_map = {}
    #     answered_ids = set()
    #     for i, response in enumerate(sub_responses):
    #         q_meta = subq_to_ask[i]
    #         answer = response["response"]["output"]["message"]["content"]
    #         answer_text = (
    #             (answer[0].get("text") or answer[0].get("solution") or "")
    #             .strip().lower()) if isinstance(answer, list) else str(answer).strip().lower()
    #         sub_answer_map[q_meta["question_id"]] = answer_text
    #
    #         enriched = layer_preprocessing(layer=2, question=q_meta, email_id=email_id, response=response,
    #                                        processed=True)
    #         sub_results.append(enriched)
    #         answered_ids.add(q_meta["question_id"])
    #
    #     # Ananswered question in layer 2
    #     for q in self.layer2:
    #         if q["question_id"] not in answered_ids:
    #             sub_results.append(layer_preprocessing(layer=2, question=q, email_id=email_id, processed=False))
    #
    #     # ========= Layer 3 =========
    #     subsub_results = []
    #     subsub_to_ask = [
    #         q for q in self.layer3
    #         if sub_answer_map.get(q["question_parent_id"]) == q.get("parent_answer", "").strip().lower()
    #     ]
    #
    #     for q in subsub_to_ask:
    #         q["email_id"] = email_id
    #
    #     subsub_question_texts = [q["question"] for q in subsub_to_ask]
    #     subsub_responses = run_llm_queries(subsub_question_texts, context_text=context)
    #
    #     # Answered questions in layer 3
    #     subsub_answered_ids = set()
    #     for i, response in enumerate(subsub_responses):
    #         q_meta = subsub_to_ask[i]
    #         enriched = layer_preprocessing(layer=3, question=q_meta, email_id=email_id, response=response,
    #                                        processed=True)
    #         subsub_results.append(enriched)
    #         subsub_answered_ids.add(q_meta["question_id"])
    #
    #     # Not answered question in layer 3
    #     for q in self.layer3:
    #         if q["question_id"] not in subsub_answered_ids:
    #             subsub_results.append(layer_preprocessing(layer=3, question=q, email_id=email_id, processed=False))
    #
    #     # ======== Clean responses =========
    #     self.clean_response_fields(results)
    #     self.clean_response_fields(sub_results)
    #     self.clean_response_fields(subsub_results)
    #
    #     return {
    #         "email_id": email_id,
    #         "main": results,
    #         "sub": sub_results,
    #         "subsub": subsub_results
    #     }

    @staticmethod
    def clean_response_fields(data_section):
        for item in data_section:
            response = item.get("response", {})
            if isinstance(response, dict):
                response.pop("stop_reason", None)
                response.pop("usage", None)
