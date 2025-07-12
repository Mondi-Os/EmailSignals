# expected schema for LLM response format
expected_schema = {
    "name": "test_schema",
    "description": "Top solutions (100 items allowed)",
    "parameters": {
        "type": "object",
        "properties": {
            "solutions": {
                "type": "array",
                "description": "List of top solutions, up to 100 items",
                "minItems": 1,
                "maxItems": 100, # default=5
                "items": {
                    "type": "object",
                    "properties": {
                        "solution": {"type": "string"},
                        "method": {
                            "type": "string",
                            "description": "Optional methodology used"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Optional rationale for this solution"
                        }
                    },
                    "required": ["solution"],
                }
            }
        },
        "required": ["solutions"],
    }
}

all_questions = load_all_questions_from_json_files(
    "C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/framework/promptsFrameworkLayer1.json",
    "C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/framework/promptsFrameworkLayer2.json",
    "C:/Users/mosmena/Desktop/Project/LLM_Project/EmailSignals/framework/promptsFrameworkLayer3.json"
)