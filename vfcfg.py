# Client credetials for Verition Fund Core API
APP = 'vf.python.client'
URI = 'vf-core-api.veritionfund.cloud:30070'
USER = 'rjohnsonperkins'
TOKEN = 'ZNMmSyIpxHUSobVGIkHKQLaXe/XWGn00WiQZj2RXKi1uI5yS0dmIqeYnDj4Mz5CeaBU0xy5NN9+g4bAVQ9GqUvB/dC87kObDEbpvA9KXYInK2KJFWaZpUuuH+DY60fVNF4JFIDxyOXtPsZ5EKmyOWpd0QafIGJyL9bqAIIvp8Ag='

# expected schema for LLM response format
expected_schema = {
    "name": "test_schema",
    "description": "Top solutions (1-5 items allowed)",
    "parameters": {
        "type": "object",
        "properties": {
            "solutions": {
                "type": "array",
                "description": "List of top solutions, up to 5 items",
                "minItems": 1,
                "maxItems": 5,
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