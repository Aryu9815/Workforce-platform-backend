IN_PROGRESS = 'In Progress'
TO_DO = 'To Do'
REVIEW = 'Review'
DONE = 'Done'
DEFAULT_STATES = [
    (TO_DO, "todo", True, False, "#999999", 1),
    (IN_PROGRESS, "in_progress", False, False, "#0275d8", 2),
    (REVIEW, "review", False, False, "#f0ad4e", 3),
    (DONE, "done", False, True, "#5cb85c", 4),
]

import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
AVAILABLE_PROVIDERS = {
    "openai": ["gpt-4o-mini", "gpt-4o"],
    "ollama": ["llama3", "mistral"]
}
TRANSITION_MAP = [
    (TO_DO, IN_PROGRESS, False),
    (IN_PROGRESS, REVIEW, False),
    (REVIEW, DONE, False),
    (REVIEW, IN_PROGRESS, False),
]

AVAILABLE="available"
ASSIGNED='assigned'
MAINTENANCE="maintenance"
LOST="lost"
DISPOSED="disposed"

AUTH_REQUIRED = 'Authentication required'
ROLE_NOT_FOUND = 'Role not found'
STAFF_NOT_FOUND = 'Staff member not found'
PROJECT_NOT_FOUND = 'Project not found'
SPRINT_NOT_FOUND = 'sprint not found'
TASK_NOT_FOUND = 'Task not found'
CLAIM_NOT_FOUND = 'Reimbursement claim not found'


STAFF_PROFILE_ID = 'staff_profiles.id'
PROJECT_ID = 'projects.id'
SET_NULL = 'SET NULL'
ROLE_ID = 'roles.id'
DEPARTMENT_ID = 'departments.id'
DESIGNATION_ID = 'designations.id'
TASK_ID = 'tasks.id'

ASIA_KOLKATA = 'Asia/Kolkata'


IMAGE_DIR = "backend/assets/member_local_images"