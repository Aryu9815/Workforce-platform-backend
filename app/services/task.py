from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from app.models.tenant import Task, TaskAssignee, Project, WorkflowState, Workflow, StaffProfile
from app.schemas import TaskCreate, TaskUpdate, TaskResponse, CommentCreate, CommentUpdate, TaskAssigneeBase
from app.services.crud import (
    task_crud, task_assignee_crud,workflow_state_crud, project_crud, staff_crud, task_comment_crud,
    task_label_crud , task_audit_crud
)
from app.services.workflow import workflow_service
from app.services.task_audit import TaskAuditService, generate_activity_messages
from app.core.constants import TASK_NOT_FOUND, PROJECT_NOT_FOUND


class TaskService:

    def __init__(self):
        """Future implementation"""
        self.task_audit_service = TaskAuditService()
        

    async def add_assignee(
        self,
        db: AsyncSession,
        task_id: str,
        user_id: str,
        role: str,
        staff_id: Optional[str] = None,
    ):
        """
        Add an assignee to a task.
        """
        if not staff_id:
            staff = await staff_crud.get_by_field(db, field="user_id", value=user_id)
            staff_id = staff.id
        return await task_assignee_crud.create(
                db,
                obj_in={
                    "task_id": task_id,
                    "staff_id": staff_id,
                    "assigned_by": user_id,
                    "role": role
                },
                user_id=user_id
            )
    
    async def add_task_assignee(
        self,
        db: AsyncSession,
        assignees: List[TaskAssigneeBase],
        task: Task,
        user_id: str
    ):
        
        added_assignees = []
        DEFAULT_ROLE_DICT = ['assignee','reporter','tester']
        [DEFAULT_ROLE_DICT.remove(assignee.role) for assignee in assignees if assignee.role != 'collaborator']
        for role in DEFAULT_ROLE_DICT:
            new_assignee = await self.add_assignee(db, task.id, user_id, role)
            added_assignees.append(new_assignee)
        
        for assignee in assignees:
            new_assignee = await task_assignee_crud.create(
                db,
                obj_in={
                    "task_id": task.id,
                    "staff_id": assignee.staff_id,
                    "assigned_by": user_id,
                    "role": assignee.role
                },
                user_id=user_id
            )
            added_assignees.append(new_assignee)
        return added_assignees
        
    async def create_task(
        self,
        db: AsyncSession,
        user_id: str,
        data: TaskCreate
    ):
        """
        Create a new project, assign creator as manager,
        and auto-create a default workflow.
        """
        project_id = data.project_id
        project = await project_crud.get(db, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=PROJECT_NOT_FOUND
            )
        all_tasks = await task_crud.get_multi(db, limit=-1, filters={"project_id": project_id, 'ticket_code':project.code})
        if len(all_tasks) > 0:
            max_ticket_number = max([task.ticket_number for task in all_tasks if task.ticket_number is not None] or [0])
            data.ticket_number = max_ticket_number + 1
        else:
            data.ticket_number = 1000
        data.ticket_code = project.code
        result = await db.execute(
            select(WorkflowState.id)
            .join(Workflow, WorkflowState.workflow_id == Workflow.id)
            .join(Project, Workflow.id == Project.workflow_id)
            .where(
                Project.id == project_id,
                WorkflowState.is_initial.is_(True),
                WorkflowState.is_active.is_(True),
                WorkflowState.is_deleted.is_(False),
            )
        )
        initial_state_id = result.scalar_one_or_none()
        if not initial_state_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Initial state not found'
            )
        task_data_dict = data.model_dump()
        task_data_dict["workflow_state_id"] = initial_state_id
        task_data_dict.pop('assignees', None)
        task = await task_crud.create(
            db,
            obj_in=task_data_dict,
            user_id=user_id
        )
        assignees = await self.add_task_assignee(db, data.assignees, task, user_id)
        await self.task_audit_service.log(
            db=db,
            task_id=task.id,
            action="CREATE",
            new_values=task_data_dict,
            performed_by=user_id
        )
        return task, assignees

    async def _check_blocked(self, db: AsyncSession, task: Task):
        if task.is_blocked_by_task:
            parent_task = await task_crud.get(db, task.parent_task_id)
            if not parent_task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent task not found"
                )
            if parent_task.completed_at is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent task is not completed"
                )

    async def update_task(
        self,
        db: AsyncSession,
        task_id: str,
        user_id: str,
        data: TaskUpdate
    ):
        """
        Update project details (allowed only for project managers).
        """
        task = await task_crud.get(db, task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=TASK_NOT_FOUND
            )
        
        await self._check_blocked(db, task)
        
        update_data_dict = data.model_dump(exclude_unset=True)
        if update_data_dict.get('workflow_state_id') and  update_data_dict.get('workflow_state_id') != task.workflow_state_id:
            is_transition_possible = await workflow_service.verify_transition(
                db,
                to_state_id=update_data_dict['workflow_state_id'],
                from_state_id=task.workflow_state_id
            )
            if not is_transition_possible:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Transition not possible"
                )
        final_state = await workflow_state_crud.get(db, update_data_dict['workflow_state_id'])
        if final_state.is_final:
            update_data_dict['completed_at'] = datetime.now(timezone.utc)

        old_values = {}
        new_values = {}
        for field, new_value in update_data_dict.items():

            old_value = getattr(task, field)

            if old_value == new_value:
                continue

            # Workflow state change
            if field == "workflow_state_id":

                old_state = await workflow_state_crud.get(db, old_value)
                new_state = await workflow_state_crud.get(db, new_value)

                old_values["status"] = {
                    "id": str(old_state.id),
                    "name": old_state.name
                }

                new_values["status"] = {
                    "id": str(new_state.id),
                    "name": new_state.name
                }

            # Task label change
            elif field == "task_label_id":

                old_label = await task_label_crud.get(db, old_value) if old_value else None
                new_label = await task_label_crud.get(db, new_value) if new_value else None

                old_values["task_label"] = {
                    "id": str(old_label.id) if old_label else None,
                    "name": old_label.label if old_label else None
                }

                new_values["task_label"] = {
                    "id": str(new_label.id) if new_label else None,
                    "name": new_label.label if new_label else None
                }

            # Priority Enum
            elif field == "priority":

                old_values[field] = old_value.value
                new_values[field] = new_value.value

            # Normal fields
            else:

                old_values[field] = old_value
                new_values[field] = new_value
                
        if new_values:
                await self.task_audit_service.log(
                    db=db,
                    task_id=task.id,
                    action="UPDATE",
                    old_values=old_values,
                    new_values=new_values,
                    performed_by=user_id
                )
                    
        updated_task = await task_crud.update(
            db,
            db_obj=task,
            obj_in=update_data_dict,
            updated_by=user_id
        )
        
        return updated_task


    async def delete_task(
        self,
        db: AsyncSession,
        task_id: str,
        user_id: str
    ):
        """
        Soft-delete a project (manager only).
        """
        task = await task_crud.get(db, task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND)
        
        # delete task assignee records 
        await task_assignee_crud.delete_by_field(
            db,
            field="task_id",
            value=task_id,
            user_id=user_id
        )
        
        # delete task comment records
        await task_comment_crud.delete_by_field(
            db,
            field="task_id",
            value=task_id,
            user_id=user_id
        )
        await self.task_audit_service.log(
            db=db,
            task_id=task.id,
            action="DELETE",
            performed_by=user_id,
            old_values={
                "title": task.title,
                "priority": task.priority,
                "workflow_state_id": task.workflow_state_id
            }
        )
        
        # delete task 
        await task_crud.delete(db, id=task_id, user_id=user_id)

        return task

    async def get_assigned_tasks_for_staff(
        self,
        db: AsyncSession,
        staff_id: UUID,
    ) -> List[Task]:

        result = await db.execute(
            select(Task)
            .join(
                TaskAssignee,
                TaskAssignee.task_id == Task.id
            )
            .where(
                TaskAssignee.staff_id == staff_id,
                TaskAssignee.is_active.is_(True),
                TaskAssignee.is_deleted.is_(False),
                Task.is_deleted.is_(False),
            )
            .order_by(Task.priority.desc(), Task.due_date.asc())
        )

        tasks = result.scalars().all()

        return tasks
    async def get_task(
        self,
        db: AsyncSession,
        task_id: str
    ) -> TaskResponse:
   
        task = await task_crud.get(db, task_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=TASK_NOT_FOUND
            )
        
        result = await db.execute(
            select(TaskAssignee, StaffProfile)
            .join(StaffProfile, StaffProfile.id == TaskAssignee.staff_id)
            .where(
                TaskAssignee.task_id == task_id,
                TaskAssignee.is_active == True,
                TaskAssignee.is_deleted == False
            )
        )
        workflow_state = await workflow_state_crud.get(db, task.workflow_state_id)
        assignees = result.all()
        task_label = None
        if task.task_label_id:
            task_label = await task_label_crud.get(db, task.task_label_id)
        audits = await task_audit_crud.get_by_fields(
            db,
            fields={"task_id": task_id}
                            )
        user_ids = {audit.performed_by for audit in audits}
        staff_result = await db.execute(
            select(StaffProfile).where(StaffProfile.user_id.in_(user_ids))
        )

        staff_list = staff_result.scalars().all()
        user_map = {
            str(staff.user_id): f"{staff.first_name} {staff.last_name}"
            for staff in staff_list
        }
        activities = generate_activity_messages(audits, user_map)
        return TaskResponse(
            id=task.id,
            title=task.title,
            task_label_id=task.task_label_id,
            task_label=task_label,
            description=task.description,
            priority=task.priority,
            estimated_hours=task.estimated_hours,
            estimated_cost=task.estimated_cost, 
            start_date=task.start_date,
            due_date=task.due_date,
            project_id=task.project_id,
            parent_task_id=task.parent_task_id,
            workflow_state_id=task.workflow_state_id,
            workflow_state_name=workflow_state.name,
            actual_hours=task.actual_hours,
            actual_cost=task.actual_cost,
            completed_at=task.completed_at,
            created_by=task.created_by,
            updated_by=task.updated_by,
            progress_percentage=task.progress_percentage,
            milestone=task.milestone,
            billable=task.billable,
            created_at=task.created_at,
            updated_at=task.updated_at,
            ticket=f"{task.ticket_code}-{task.ticket_number}" if task.ticket_code and task.ticket_number else None,
            ticket_code=task.ticket_code,
            ticket_number=task.ticket_number,
            assignees=[
                {
                    'assignee_id': assignee.id,
                    'name': f"{staff.first_name} {staff.last_name}",
                    'allocation_percentage': assignee.allocation_percentage, 
                    'role': assignee.role,
                }
                for assignee, staff in assignees
            ],
             # ⭐ ADD THIS
            audit_logs=audits,
            activities=activities,
        )

    async def add_task_comment(
        self,
        db: AsyncSession,
        data: CommentCreate,
        user_id: str    
    ):
        """
        Add a comment to a task.
        """
        task = await task_crud.get(db, data.task_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=TASK_NOT_FOUND
            )
        
        comment_data = data.model_dump()
        comment_data["user_id"] = user_id
        
        comment = await task_comment_crud.create(
            db,
            obj_in=comment_data,
            user_id=user_id
        )
        await self.task_audit_service.log(
            db=db,
            task_id=data.task_id,
            action="COMMENT_ADDED",
            new_values={"comment_id": comment.id},
            performed_by=user_id
        )
        return comment, task
    
    async def get_comments(
        self,
        db: AsyncSession,
        task_id: str
    ):
        """
        Get all comments for a task.
        """
        task = await task_crud.get(db, task_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=TASK_NOT_FOUND
            )
        
        comments = await task_comment_crud.get_by_fields(
            db,
            fields={"task_id": task_id}
        )
        return comments
    
    async def delete_comment(
        self,
        db: AsyncSession,
        comment_id: str,
        user_id: str
    ):
        """
        Delete a comment.
        """
        comment = await task_comment_crud.get(db, comment_id)
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        if str(comment.user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this comment"
            )
        await task_comment_crud.delete(db, id=comment_id, user_id=user_id)
        return True
    
    async def update_comment(
        self,
        db: AsyncSession,
        comment_id: str,
        user_id: str,
        data: CommentUpdate
    ):
        """
        Update a comment.
        """
        comment = await task_comment_crud.get(db, comment_id)
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
        updated_comment = await task_comment_crud.update(
            db,
            db_obj=comment,
            obj_in=data.model_dump(exclude_unset=True),
            updated_by=user_id
        )
        return updated_comment

    async def get_backlogs(self, db: AsyncSession, project_id: str):
        """
        Get all backlog tasks for a project.
        """
        tasks = await task_crud.get_multi(
            db,
            limit=-1,
            filters={'sprint_id': None, 'project_id': project_id}
        )
    
        task_responses = []
        for task in tasks:
            state = await workflow_state_crud.get(db, task.workflow_state_id)
            task_responses.append(TaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                priority=task.priority,
                estimated_hours=task.estimated_hours,
                estimated_cost=task.estimated_cost,
                start_date=task.start_date,
                due_date=task.due_date,
                project_id=task.project_id,
                parent_task_id=task.parent_task_id,
                workflow_state_id=task.workflow_state_id,
                workflow_state_name=state.name if state else None,
                actual_hours=task.actual_hours,
                actual_cost=task.actual_cost,
                completed_at=task.completed_at,
                created_by=task.created_by,
                progress_percentage=task.progress_percentage,
                milestone=task.milestone,
                billable=task.billable,
                created_at=task.created_at,
                updated_at=task.updated_at,
                assignees=[],
                ticket=f"{task.ticket_code}-{task.ticket_number}" if task.ticket_code and task.ticket_number else None,
                ticket_code=task.ticket_code,
                ticket_number=task.ticket_number
            ))
        return task_responses

    async def get_ticket(self, db: AsyncSession, sprint_id: UUID):
        tasks = await task_crud.get_multi(
            db,
            limit=-1,
            filters={'sprint_id': sprint_id}
        )
        return {task.id: f"{task.ticket_code}-{task.ticket_number}"  for task in tasks}
        

task_service = TaskService()