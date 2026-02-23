"""
PandaPulse Tool Definitions
These schemas allow the AI to 'act' on the database. 
Updated to match Applicant/Employer model architecture.
"""

CHATBOT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_profile",
            "description": "Updates the authenticated user's profile. Use this when a user updates their headline, skills, or company info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "headline": {
                        "type": "string",
                        "description": "APPLICANT ONLY: A short professional tagline (e.g., 'Senior Fullstack Engineer')."
                    },
                    "skills": {
                        "type": "string",
                        "description": "APPLICANT ONLY: Comma-separated list of technical/soft skills."
                    },
                    "location": {
                        "type": "string",
                        "description": "The user's current city, state, or 'Remote'."
                    },
                    "company_name": {
                        "type": "string",
                        "description": "EMPLOYER ONLY: The name of the hiring organization."
                    },
                    "company_description": {
                        "type": "string",
                        "description": "EMPLOYER ONLY: Information about the company's mission and culture."
                    }
                },
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_job_application",
            "description": "Submits a formal application for a job. Call this when an applicant confirms they want to apply for a Job ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "integer",
                        "description": "The numerical database ID of the job."
                    },
                    "cover_letter": {
                        "type": "string",
                        "description": "A tailored cover letter using Markdown."
                    }
                },
                "required": ["job_id", "cover_letter"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_jobs",
            "description": "Queries the database for open roles. Useful for 'What's new?' or specific keyword searches.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "Search terms for titles, skills, or company names."
                    },
                    "location": {
                        "type": "string",
                        "description": "Filter by city or 'Remote'."
                    }
                },
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_direct_message",
            "description": "Sends a message to another user. Use for networking or follow-ups.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient_username": {
                        "type": "string",
                        "description": "The target user's username."
                    },
                    "body": {
                        "type": "string",
                        "description": "Message content. Keep it professional."
                    }
                },
                "required": ["recipient_username", "body"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_job_posting",
            "description": "Creates a new job listing. Strictly restricted to Employer accounts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The job title."
                    },
                    "description": {
                        "type": "string",
                        "description": "Full job details in Markdown."
                    },
                    "location": {
                        "type": "string",
                        "description": "City/State or 'Remote'."
                    },
                    "salary_range": {
                        "type": "string",
                        "description": "Pay estimate (e.g., '$90k - $120k')."
                    }
                },
                "required": ["title", "description", "location"],
                "additionalProperties": False
            }
        }
    }
]