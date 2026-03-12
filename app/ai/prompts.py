TASK_SUMMARY_PROMPT = """
You are an ERP productivity assistant.

Summarize this task:

{task_description}

Provide:
- Short summary
- Priority
- Key action items
"""


PROFESSIONAL_MESSAGE_PROMPT = """
Rewrite the following message professionally:

Message:
{message}

Return a clear and professional response.
"""



PROMPTS = {
    "professional_message": PROFESSIONAL_MESSAGE_PROMPT
}