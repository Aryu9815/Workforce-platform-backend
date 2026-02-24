from warnings import filters

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from app.models.tenant import Task, TaskAssignee, TaskComment, TaskDependency, Project, WorkflowState, Workflow, StaffProfile
from app.schemas.task_schemas import TaskCreate, TaskUpdate, TaskResponse, CommentCreate, CommentUpdate
from app.services.crud import CRUDService
from datetime import datetime, timezone
from app.services.workflow import WorkflowService



class TaskService:

    def __init__(self):
        self.task_crud = CRUDService(Task)
        self.task_assignee_crud = CRUDService(TaskAssignee)
        self.task_comment_crud = CRUDService(TaskComment)
        self.task_dependency_crud = CRUDService(TaskDependency)
        self.workflow_service = WorkflowService()
        self.workflow_state_crud = CRUDService(WorkflowState)
        self.project_crud = CRUDService(Project)


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
        project = await self.project_crud.get(db, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        all_tasks = await self.task_crud.get_multi(db, limit=-1, filters={"project_id": project_id, 'ticket_code':project.code})
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
        task_data_dict["created_by"] = user_id
        del task_data_dict['assignee_ids']
        task = await self.task_crud.create(
            db,
            obj_in=task_data_dict,
        )
        for assignee_id in data.assignee_ids:
            await self.task_assignee_crud.create(
                db,
                obj_in={
                    "task_id": task.id,
                    "staff_id": assignee_id,
                    "assigned_by": user_id,
                    "is_primary": assignee_id == data.assignee_ids[0] if data.assignee_ids else False
                },
                user_id=user_id
            )
        return task


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
        task = await self.task_crud.get(db, task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        update_data_dict = data.model_dump(exclude_unset=True)
        if update_data_dict.get('workflow_state_id'):
            is_transition_possible = await self.workflow_service.verify_transition(
                db,
                to_state_id=update_data_dict['workflow_state_id'],
                from_state_id=task.workflow_state_id
            )
            if not is_transition_possible:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Transition not possible"
                )
            
        updated_task = await self.task_crud.update(
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
        task = await self.task_crud.get(db, task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
        # delete task assignee records 
        await self.task_assignee_crud.delete_by_field(
            db,
            field="task_id",
            value=task_id,
            user_id=user_id
        )
        
        # delete task comment records
        await self.task_comment_crud.delete_by_field(
            db,
            field="task_id",
            value=task_id,
            user_id=user_id
        )
        
        # delete task 
        await self.task_crud.delete(db, id=task_id, user_id=user_id)

        return task


    async def get_task(
        self,
        db: AsyncSession,
        task_id: str
    ) -> TaskResponse:
   
        task = await self.task_crud.get(db, task_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
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
        workflow_state = await self.workflow_state_crud.get(db, task.workflow_state_id)
        assignees = result.all()

        return TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            task_type=task.task_type,
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
                    'is_primary': assignee.is_primary,
                    'allocation_percentage': assignee.allocation_percentage
                }
                for assignee, staff in assignees
            ]
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
        task = await self.task_crud.get(db, data.task_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        comment_data = data.model_dump()
        comment_data["user_id"] = user_id
        
        comment = await self.task_comment_crud.create(
            db,
            obj_in=comment_data,
            user_id=user_id
        )
        return comment
    
    async def get_comments(
        self,
        db: AsyncSession,
        task_id: str
    ):
        """
        Get all comments for a task.
        """
        task = await self.task_crud.get(db, task_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        comments = await self.task_comment_crud.get_by_fields(
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
        comment = await self.task_comment_crud.get(db, comment_id)
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
        await self.task_comment_crud.delete(db, id=comment_id, user_id=user_id)
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
        comment = await self.task_comment_crud.get(db, comment_id)
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
        updated_comment = await self.task_comment_crud.update(
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
        tasks = await self.task_crud.get_multi(
            db,
            limit=-1,
            filters={'sprint_id': None, 'project_id': project_id}
        )
    
        task_responses = []
        for task in tasks:
            state = await self.workflow_state_crud.get(db, task.workflow_state_id)
            task_responses.append(TaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                priority=task.priority,
                task_type=task.task_type,
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