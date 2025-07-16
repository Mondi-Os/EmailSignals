from bson import ObjectId
from clientRequests.VFModelsRequest import *
from datetime import datetime
import sys

class LLMPipeline:

    def __init__(self):
        self.questions = []

        prompts = prompts_collection.find({}, {"_id": 0})
        for prompt in prompts:
            self.questions.append(prompt)

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
            output_questions = result["questions"]

            # Email result solutions
            email_result_dict = {
                "email_info": email_info,
                "questions": output_questions
            }

            # Normalize the structure of solutions
            email_result = normalize_solutions_structure(email_result_dict)

            # Upsert into 'result' collection
            result_collection.update_one({"source_id": ObjectId(email_id)}, {"$set": email_result}, upsert=True)
            print(f"Upserted email_id {email_id} into 'result' collection.")

        end_time = datetime.now()
        print(f"Pipeline finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total duration: {end_time - start_time}\n")

    def run_single(self, email_id, context):
        processed_results, answer_map, cached_stats = [], {}, {}

        # Pre-calculate total questions per layer
        for q in self.questions:
            layer = q.get("layer", 1) # making sure each question has a layer value otherwise set to 1
            cached_stats.setdefault(layer, {"processed": 0, "from_cache": 0, "total": 0})
            cached_stats[layer]["total"] += 1

        for question in self.questions:
            parent_id = question.get("question_parent_id")
            layer = question.get("layer", 1)

            # Check dependency logic
            if parent_id:
                parent_answer = answer_map.get(parent_id, "").strip().lower()
                expected_answer = question.get("parent_answer", "yes").strip().lower()
                if parent_answer != expected_answer:
                    continue

            llm_result = cache_or_llm(question, context)
            answer_text = extract_answer_text(llm_result["response"]["output"]["message"]["content"])
            answer_map[question["question_id"]] = answer_text

            # Enrich and store result
            enriched = layer_preprocessing(
                layer=layer,
                question=question,
                email_id=email_id,
                response=llm_result["response"],
                processed=True
            )
            processed_results.append(enriched)

            # Update cached info
            cached_stats[layer]["processed"] += 1
            if llm_result["from_cache"]:
                cached_stats[layer]["from_cache"] += 1

        self.clean_response_fields(processed_results)

        # Print summary for each layer
        for layer, stats in sorted(cached_stats.items()):
            print(f"Layer{layer}::::  processed: {stats['processed']}/{stats['total']}  |||  from_cache: {stats['from_cache']} / {stats['processed']}")

        return {
            "email_id": email_id,
            "questions": processed_results + get_unprocessed(self.questions, processed_results)
        }

    # def run_single(self, email_id, context):
    #     """Run LLM pipeline for a single email body."""
    #     layer1_cache_hits, layer2_cache_hits, layer3_cache_hits = 0, 0, 0
    #     q_processed_1, q_processed_2, q_processed_3 = 0, 0 ,0
    #
    #     # =============== Layer 1 ===============
    #     results, main_answer_map = [], {}
    #     for i, question in enumerate(self.layer1):
    #         question = self.layer1[i]
    #         llm_result_1 = cache_or_llm(question, context)
    #         q_processed_1 += 1
    #         if llm_result_1["from_cache"]:
    #             layer1_cache_hits += 1
    #         answer_text = extract_answer_text(llm_result_1["response"]["output"]["message"]["content"])
    #         main_answer_map[question["question_id"]] = answer_text
    #         results.append(layer_preprocessing(layer=1, question=question, email_id=email_id, response=llm_result_1["response"], processed=True))
    #     print(f"Layer1::::  processed: {q_processed_1}/{len(self.layer1)}  |||  from_cache: {layer1_cache_hits} / {q_processed_1}")
    #
    #     # =============== Layer 2 ===============
    #     sub_results, sub_answer_map, answered_ids = [], {}, set()
    #     for i, q in enumerate(self.layer2):
    #         if main_answer_map.get(q["question_parent_id"]) != "yes":
    #             continue
    #         llm_result_2 = cache_or_llm(q, context)
    #         q_processed_2 += 1
    #         if llm_result_2["from_cache"]:
    #             layer2_cache_hits += 1
    #         answer_text = extract_answer_text(llm_result_2["response"]["output"]["message"]["content"])
    #         sub_answer_map[q["question_id"]] = answer_text
    #         sub_results.append(layer_preprocessing(layer=2, question=q, email_id=email_id, response=llm_result_2["response"], processed=True))
    #     print(f"Layer2::::  processed: {q_processed_2}/{len(self.layer2)}  |||  from_cache: {layer2_cache_hits} / {q_processed_2}")
    #
    #     # =============== Layer 3 ===============
    #     subsub_results = []
    #     for q in self.layer3:
    #         if sub_answer_map.get(q["question_parent_id"]) != q.get("parent_answer", "").strip().lower():
    #             continue
    #         llm_result_3 = cache_or_llm(q, context)
    #         q_processed_3 += 1
    #         if llm_result_3["from_cache"]:
    #             layer3_cache_hits += 1
    #         subsub_results.append(layer_preprocessing(layer=3, question=q, email_id=email_id, response=llm_result_3["response"], processed=True))
    #     print(f"Layer3::::  processed: {q_processed_3}/{len(self.layer3)}  |||  from_cache: {layer3_cache_hits} / {q_processed_3}")
    #
    #     # ============== Clean up ===============
    #     self.clean_response_fields(results)
    #     self.clean_response_fields(sub_results)
    #     self.clean_response_fields(subsub_results)
    #
    #     return {
    #         "email_id": email_id,
    #         "questions": results + sub_results + subsub_results +
    #                      get_unprocessed(self.layer1, results) +
    #                      get_unprocessed(self.layer2, sub_results) +
    #                      get_unprocessed(self.layer3, subsub_results)
    #     }

    @staticmethod
    def clean_response_fields(data_section):
        for item in data_section:
            response = item.get("response", {})
            if isinstance(response, dict):
                response.pop("stop_reason", None)
                response.pop("usage", None)


# pipeline = LLMPipeline()
# pipeline.run_batch(fetch_emails_from_database(filter_dict={}, limit=2)) # filtering: {"from": "ewan.gordon@socgen.com"}