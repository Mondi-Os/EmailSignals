from bson import ObjectId
from datetime import datetime
from clientRequests.VFModelsRequest import *
from credentials.vfcfg import *
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
                    "from": email.get("from"),
                    "subject": email.get("subject"),
                    "to": email.get("to")
            }
            print(f"Processing email ID: {email_id}")

            # Execute the run_single() to go through the question layers
            result = self.run_single(email_id, context)
            output_questions = result["questions"]
            processed_info = result.get("layer0_fields", {})

            # Collection Email Record
            email_result_dict = {
                "email_info": email_info,
                "processed_info": processed_info,
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
        processed_results, annotated_questions, answer_map, cached_stats, layer0_fields = [], [], {}, {}, {}

        # Display information: Pre-calculate total questions per layer
        for q in self.questions:
            layer = q.get("layer", 1) # making sure each question has a layer value otherwise set to 1
            cached_stats.setdefault(layer, {"processed": 0, "from_cache": 0, "total": 0})
            cached_stats[layer]["total"] += 1

        for question in self.questions:
            parent_id = question.get("question_parent_id")
            layer = question.get("layer", 1) # Set layer 1 for question that have no layer

            # Check dependency logic
            if parent_id:
                parent_answer = answer_map.get(parent_id, "").strip().lower()
                expected_answer = question.get("parent_answer", "yes").strip().lower()
                if parent_answer != expected_answer:
                    continue

            # Check cache or call LLM
            llm_result, answer_text = cache_or_llm(question, context)
            answer_map[question["question_id"]] = answer_text

            if layer == 0:
                normalized_question = normalize_solutions_structure({"questions": [{"response": llm_result["response"]}]})["questions"][0]
                try:
                    solution = normalized_question["response"]["output"]["message"]["content"]["solutions"][0]["solution"]
                except (KeyError, IndexError, TypeError):
                    solution = None
                layer0_fields[question["ref"]] = solution
                cached_stats[layer]["processed"] += 1
                if llm_result["from_cache"]:
                    cached_stats[layer]["from_cache"] += 1
                continue  # skip appending to processed_results

            # Enrich and store result
            enriched = layer_preprocessing(layer=layer, question=question, response=llm_result["response"])
            processed_results.append(enriched)

            # Display information: Update cached info
            cached_stats[layer]["processed"] += 1
            if llm_result["from_cache"]:
                cached_stats[layer]["from_cache"] += 1

        self.clean_response_fields(processed_results)

        # Display information: Print summary for each layer
        for layer, stats in sorted(cached_stats.items()):
            print(f"Layer{layer}::::  processed: {stats['processed']} / {stats['total']}  |||  from_cache: {stats['from_cache']} / {stats['processed']}")

        return {
            "email_id": email_id,
            "questions": processed_results + get_unprocessed(self.questions, processed_results),
            "layer0_fields": layer0_fields
        }

    @staticmethod
    def clean_response_fields(data_section):
        for item in data_section:
            response = item.get("response", {})
            if isinstance(response, dict):
                response.pop("stop_reason", None)
                response.pop("usage", None)


pipeline = LLMPipeline()
pipeline.run_batch(fetch_emails_from_database(filter_dict={}, limit=50)) # filtering: {"from": "ewan.gordon@socgen.com"}