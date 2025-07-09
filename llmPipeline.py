from clientRequests.VFModelsRequest import *

import matplotlib.pyplot as plt
import networkx as nx
import os
import json

class LLMPipeline:
    def __init__(self):
        with open("framework/promptsFrameworkMain.json") as f:
            self.main_questions = json.load(f)
        with open("framework/promptsFrameworkBranches.json") as f:
            self.sub_questions = json.load(f)

    def run_batch(self, email_docs, enable_tree_for=None):
        """
        Run LLM pipeline for multiple emails (parsed_docs), save each email separately.
        """
        from datetime import datetime
        import os
        import json

        start_time = datetime.now()
        print(f"Pipeline started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        enable_tree_for = set(enable_tree_for or [])
        output_dir = "review_results"
        os.makedirs(output_dir, exist_ok=True)

        for email in email_docs:
            email_id = str(email["_id"])
            context = str(email["body"])
            print(f"Processing email ID: {email_id}")

            output = self.run_single(email_id, context)

            # Wrap each result in its own file with metadata
            email_result = {
                "email_info": {
                    "_id": email_id,
                    "date": email.get("date"),
                    "from": email.get("from")
                },
                "main": output["main"],
                "sub": output["sub"]
            }

            # Generate tree only if requested
            if email_id in enable_tree_for:
                self.generate_tree_diagram(output)

            # Save per-email result
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{timestamp}--{email_id}.json"
            output_path = os.path.join(output_dir, filename)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(email_result, f, indent=2, ensure_ascii=False)

        end_time = datetime.now()
        print(f"Pipeline finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total duration: {end_time - start_time}")

    def run_single(self, email_id, context):
        """
        Run for a single email body.
        """
        # Run main questions
        main_question_texts = [q["question"] for q in self.main_questions]
        main_responses = run_llm_queries(main_question_texts, context_text=context)

        results = []
        for i, response in enumerate(main_responses):
            enriched = {
                "question_id": self.main_questions[i]["question_id"],
                "revision": self.main_questions[i]["revision"],
                "ref": self.main_questions[i]["ref"],
                "question": self.main_questions[i]["question"],
                "email_id": email_id,
                "response": response["response"]
            }
            results.append(enriched)

        # Decide which subquestions to ask
        subq_to_ask = []
        for result in results:
            answer_content = result["response"]["output"]["message"]["content"]
            answer_text = answer_content[0]["text"].strip().lower() if isinstance(answer_content, list) else str(answer_content).strip().lower()
            if answer_text == "yes":
                matching_subqs = [
                    q for q in self.sub_questions
                    if q.get("parent_id") == result["question_id"] or q.get("question_parent_id") == result["question_id"]
                ]
                for q in matching_subqs:
                    q_copy = q.copy()
                    q_copy["email_id"] = email_id
                    subq_to_ask.append(q_copy)

        # Run subquestions
        sub_question_texts = [q["question"] for q in subq_to_ask]
        sub_responses = run_llm_queries(sub_question_texts, context_text=context)

        sub_results = []
        for i, response in enumerate(sub_responses):
            enriched = {
                "question_id": subq_to_ask[i].get("id") or subq_to_ask[i].get("question_id"),
                "parent_id": subq_to_ask[i].get("parent_id") or subq_to_ask[i].get("question_parent_id"),
                "revision": subq_to_ask[i]["revision"],
                "ref": subq_to_ask[i]["ref"],
                "question": subq_to_ask[i]["question"],
                "email_id": email_id,
                "response": response["response"]
            }
            sub_results.append(enriched)

        # Clean responses
        self.clean_response_fields(results)
        self.clean_response_fields(sub_results)

        return {
            "email_id": email_id,
            "main": results,
            "sub": sub_results
        }

    def generate_tree_diagram(self, email_output):
        """
        Generate a vertical question flow tree: Email -> Main -> Sub.
        """
        email_id = str(email_output["email_id"])
        G = nx.DiGraph()

        # Add root node
        G.add_node(email_id, level=0)

        # Structure levels
        level_1 = []  # main questions
        level_2 = []  # subquestions

        main = email_output["main"]
        sub = email_output["sub"]

        for q in main:
            qid = str(q["question_id"])
            G.add_node(qid, level=1)
            G.add_edge(email_id, qid)
            level_1.append(qid)

            answer = q["response"]["output"]["message"]["content"][0]["text"].strip().lower()
            if answer == "yes":
                for subq in sub:
                    if str(subq.get("parent_id")) == str(q["question_id"]):
                        sub_id = str(subq["question_id"])
                        G.add_node(sub_id, level=2)
                        G.add_edge(qid, sub_id)
                        level_2.append(sub_id)

        # Custom vertical layout by level
        pos = {}
        layer_spacing = 2
        node_spacing = 2

        levels = {0: [email_id], 1: level_1, 2: level_2}
        for lvl, nodes in levels.items():
            for i, node in enumerate(nodes):
                pos[node] = (i * node_spacing, -lvl * layer_spacing)

        # Draw
        plt.figure(figsize=(10, 6))
        nx.draw(
            G, pos, with_labels=True, node_color="lightblue",
            node_size=1200, font_size=10, arrows=True
        )
        plt.title(f"LLM Tree for Email {email_id} (Top-Down View)")

        # Save
        os.makedirs("review_results/trees", exist_ok=True)
        path = f"review_results/trees/{email_id}_tree.png"
        plt.savefig(path)
        plt.close()

    @staticmethod
    def clean_response_fields(data_section):
        for item in data_section:
            response = item.get("response", {})
            if isinstance(response, dict):
                response.pop("stop_reason", None)
                response.pop("usage", None)

pipeline = LLMPipeline()
pipeline.run_batch(email_info) # additioanl param enable_tree_for=["686e0cb099a8bf938dc2aab1", "686cd28040209effb126ac8d"]