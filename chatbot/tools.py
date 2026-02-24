CHATBOT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_profile",
            "description": "Updates the authenticated user's profile fields.",
            "parameters": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "skills": {"type": "string"},
                    "location": {"type": "string"},
                    "company_name": {"type": "string"},
                    "company_description": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_job_application",
            "description": "Submit an application for a job ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "integer"},
                    "cover_letter": {"type": "string"},
                },
                "required": ["job_id", "cover_letter"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_jobs",
            "description": "Search open jobs by keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {"type": "string"},
                    "location": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_direct_message",
            "description": "Send a direct message to another user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient_username": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["recipient_username", "body"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_job_posting",
            "description": "Create a new job posting for employer accounts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                    "salary_range": {"type": "string"},
                },
                "required": ["title", "description", "location"],
                "additionalProperties": False,
            },
        },
    },
]
