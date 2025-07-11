from clientRequests.VFModelsRequest import *
from datetime import datetime
from llmCache import *

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

        all_questions = load_all_questions_from_json_files(
            "C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/framework/promptsFrameworkLayer1.json",
            "C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/framework/promptsFrameworkLayer2.json",
            "C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/framework/promptsFrameworkLayer3.json"
            )

        for email in email_docs:
            email_id = str(email["_id"])
            context = str(email["body"])
            print(f"Processing email ID: {email_id}")

            # Load from LLM cache if exists
            cached_output = llm_simulation(
                questions=all_questions,
                email_body=context
            )

            if cached_output:
                output_dir = "review_results/simulator_results"
                output_questions = cached_output["questions"]
                email_info = {
                    "_id": email_id,
                    "date": email.get("date"),
                    "from": email.get("from")
                }
            else:
                output_dir = "review_results"
                result = self.run_single(email_id, context)
                output_questions = result["main"] + result["sub"] + result["subsub"]
                email_info = {
                    "_id": email_id,
                    "date": email.get("date"),
                    "from": email.get("from")
                }

            # Final result format
            email_result = {
                "email_info": email_info,
                "questions": output_questions
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

            # Extract answer text based on the response format (sometimes LLM returns "text" and sometimes "solution")
            if isinstance(answer, list) and "json" in answer[0]:
                answer_text = (
                    answer[0]["json"]["solutions"][0]["solution"].strip().lower()
                    if answer[0]["json"].get("solutions") else ""
                )
            else:
                answer_text = (
                    (answer[0].get("text") or answer[0].get("solution") or "")
                    .strip()
                    .lower()
                    if isinstance(answer, list) else str(answer).strip().lower()
                )

            main_answer_map[question["question_id"]] = answer_text
            enriched = {
                "question_id": question["question_id"],
                "ref": question["ref"],
                "question": question["question"],
                "email_id": email_id,
                "response": response,
                "processed": True,
                "layer": question.get("layer", 1)
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
            answer_text = (
                (answer[0].get("text") or answer[0].get("solution") or "")
                .strip().lower()) if isinstance(answer, list) else str(answer).strip().lower()
            sub_answer_map[q_meta["question_id"]] = answer_text

            enriched = {
                "question_id": q_meta.get("id") or q_meta.get("question_id"),
                "parent_id": q_meta.get("parent_id") or q_meta.get("question_parent_id"),
                "ref": q_meta["ref"],
                "question": q_meta["question"],
                "email_id": email_id,
                "response": response,
                "processed": True,
                "layer": q_meta.get("layer", 2)
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
                    "processed": False,
                    "layer": q.get("layer", 2)
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
        subsub_responses = run_llm_queries(subsub_question_texts, context_text=context)

        # Answered questions in layer 3
        subsub_answered_ids = set()
        for i, response in enumerate(subsub_responses):
            q_meta = subsub_to_ask[i]
            enriched = {
                "question_id": q_meta.get("id") or q_meta.get("question_id"),
                "parent_id": q_meta.get("parent_id") or q_meta.get("question_parent_id"),
                "ref": q_meta["ref"],
                "question": q_meta["question"],
                "email_id": email_id,
                "response": response,
                "processed": True,
                "layer": q_meta.get("layer", 3)
            }
            subsub_results.append(enriched)
            subsub_answered_ids.add(q_meta["question_id"])

        # Not answered question in layer 3
        for q in self.layer3:
            if q["question_id"] not in subsub_answered_ids:
                subsub_results.append({
                    "question_id": q["question_id"],
                    "parent_id": q.get("question_parent_id"),
                    "ref": q["ref"],
                    "question": q["question"],
                    "email_id": email_id,
                    "processed": False,
                    "layer": q.get("layer", 3)
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
pipeline.run_batch(fetch_emails_from_database(filter_dict={"from": "ewan.gordon@socgen.com"}, limit=1))