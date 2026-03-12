from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.tenant import TaskAudit
from uuid import UUID
from datetime import datetime, date
from enum import Enum

def generate_activity_messages(audits, user_map):

    activities = []

    for audit in audits:

        user_name = user_map.get(str(audit.performed_by), f"Someone {audit.performed_by}")

        old = audit.old_values or {}
        new = audit.new_values or {}

        # HANDLE CREATE
        if audit.action == "CREATE":
            title = new.get("title")
            activities.append(f'{user_name} created task "{title}"')
            continue
        elif audit.action == "COMMENT_ADDED":
            activities.append(f'{user_name} added a comment')
            continue
        for field in new.keys():

            # STATUS
            if field == "status":
                old_name = old.get(field, {}).get("name")
                new_name = new.get(field, {}).get("name")

                activities.append(
                    f'{user_name} changed status from "{old_name}" → "{new_name}"'
                )

            # PRIORITY
            elif field == "priority":

                old_val = old.get(field)
                new_val = new.get(field)

                if old_val is None:
                    activities.append(
                        f'{user_name} set priority to "{new_val}"'
                    )
                else:
                    activities.append(
                        f'{user_name} changed priority from "{old_val}" → "{new_val}"'
                    )

            # DUE DATE
            elif field == "due_date":

                old_val = old.get(field)
                new_val = new.get(field)

                if old_val:
                    activities.append(
                        f'{user_name} changed due date from "{old_val}" → "{new_val}"'
                    )
                else:
                    activities.append(
                        f'{user_name} set due date to "{new_val}"'
                    )

            # TITLE
            elif field == "title":
                activities.append(
                    f'{user_name} updated the title'
                )

            # DESCRIPTION
            elif field == "description":
                activities.append(
                    f'{user_name} updated the description'
                )

            # LABEL
            elif field == "task_label":
                activities.append(
                    f'{user_name} changed label from "{old.get(field, {}).get("name")}" → "{new.get(field, {}).get("name")}"'
                )

            # HOURS
            elif field == "estimated_hours":

                old_val = old.get(field)
                new_val = new.get(field)

                if old_val is None:
                    activities.append(
                        f'{user_name} set estimated hours to {new_val}'
                    )
                else:
                    activities.append(
                        f'{user_name} updated estimated hours from {old_val} → {new_val}'
                    )

    return activities
def make_json_serializable(data):
    if isinstance(data, dict):
        return {k: make_json_serializable(v) for k, v in data.items()}

    if isinstance(data, list):
        return [make_json_serializable(v) for v in data]

    if isinstance(data, UUID):
        return str(data)

    if isinstance(data, datetime):
        return data.isoformat()

    if isinstance(data, date):
        return data.isoformat()

    if isinstance(data, Enum):
        return data.value

    return data
class TaskAuditService:

    async def log(
        self,
        db: AsyncSession,
        task_id: UUID,
        action: str,
        performed_by: UUID,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
    ):
        old_values = make_json_serializable(old_values)
        new_values = make_json_serializable(new_values)
        audit = TaskAudit(
            task_id=task_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            performed_by=performed_by
        )

        db.add(audit)

        # flush ensures FK validation + insert execution
        await db.flush()