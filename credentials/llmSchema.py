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