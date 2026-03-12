from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from typing import List
from app.models.tenant import (
    StaffProfile, RolePermission, 
    Sprint, ProjectMember, 
    Task, TaskAssignee, Department,
    Designation, WorkflowState, WorkflowTransitions, Notifications
)
from app.models.common import PushSubscription
from app.schemas import  NotificationResponse
from app.db.base import get_common_session_maker
from app.utils.email_templates import SPRINT_END, STAFF_JOINING, STAFF_REMOVE, TASK_ASSIGNED, TASK_COLLABARATED, ADD_MEMBER, TASK_INCOMPLETE_ALERT
from app.services.crud import (
    staff_crud, project_crud, project_member_crud, task_crud, task_assignee_crud,
    workflow_state_crud, notification_crud,
    notification_jobs_crud, permission_crud, tenant_user_role_crud
)
from datetime import datetime, timezone, date, timedelta
from sqlalchemy import or_
from app.utils.cache_utils import cache_utils

class NotificationService:

    async def create_notification(
        self,
        data: dict,
    ):
        """
        Create a new project, assign creator as manager,
        and auto-create a default workflow.
        """
        session_maker = await get_common_session_maker()
        async with session_maker() as db:
            notification = await notification_crud.create(
                db,
                obj_in=data
            )
            await db.commit()
            await db.refresh(notification)   
        notification_data = {
            "id":notification.id,
            "tenant_id":notification.tenant_id,
            "user_id":notification.user_id,
            "title":notification.title,
            "message":notification.message,
            "entity_type":notification.entity_type,
            "entity_id":notification.entity_id,
            "is_read":notification.is_read,
            "created_at":notification.created_at
        } 
        await cache_utils.set_user_notifications_cache(data['user_id'], data['tenant_id'], notification_data)
        return notification

    async def enqueue_notification_job(
        self,
        tenant_id: str,
        notification_id: str,
        channel: str,
        payload: dict
    ):
        """
        Enqueue a notification job.
        """
        session_maker = await get_common_session_maker()
        async with session_maker() as db:
            notification_job = await notification_jobs_crud.create(
                db,
                obj_in={
                    "notification_id": notification_id,
                    "channel": channel,
                    "payload": payload,
                    "tenant_id": tenant_id
                }
            )
            await db.commit()
            await db.refresh(notification_job)
            if not notification_job:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to enqueue notification job")
        return notification_job

    async def get_notifications(self, user_id: str, tenant_id: str) -> List[NotificationResponse]:
        """
        Get all notifications for a user.
        """
        notifications = await cache_utils.get_user_notifications_cache(user_id, tenant_id)
        if notifications:
            
            return notifications
        else:
            session_maker = await get_common_session_maker()
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            async with session_maker() as db:
                notifications = await notification_crud.get_multi(
                    db,
                    filters={"user_id": user_id},
                    extra_conditions=[
                        or_(
                            Notifications.created_at >= yesterday,
                            Notifications.is_read == False
                        )
                    ]
                )
            return [
                NotificationResponse(
                    id=notification.id,
                    tenant_id=notification.tenant_id,
                    user_id=notification.user_id,
                    title=notification.title,
                    message=notification.message,
                    entity_type=notification.entity_type,
                    entity_id=notification.entity_id,
                    is_read=notification.is_read,
                    created_at=notification.created_at
                )
                for notification in notifications
            ]
    
    async def mark_notification_as_read(self, notification_id: str, user_id: str):
        """
        Mark a notification as read.
        """
        session_maker = await get_common_session_maker()
        async with session_maker() as db:
            notification = await notification_crud.get(db, id=notification_id)
            if not notification:
               raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        
            await notification_crud.update(
                db,
                db_obj=notification,
                obj_in={"is_read": True},
                updated_by=user_id
            )
            await db.commit()
            await db.refresh(notification)
        return notification
    
    async def push_subscribe(self, common_user_id: str, tenant_id: str, sub: dict):
        
        session_maker = await get_common_session_maker()
        async with session_maker() as db:
            exist = await db.execute(
                PushSubscription.__table__.select()
                .where(PushSubscription.user_id == common_user_id)
            )

            if exist.first():
                return {"message": "Already subscribed"}

            new_sub = PushSubscription(
                id=str(uuid4()),
                tenant_id=tenant_id,
                user_id=common_user_id,
                endpoint=sub["endpoint"],
                p256dh=sub["keys"]["p256dh"],
                auth=sub["keys"]["auth"]
            )

            db.add(new_sub)
            await db.commit()

        return {"message": "Subscription saved"}

    async def notify_role_permissions(self, db: AsyncSession, role_permission: RolePermission, tenant_id: str, user_id: str):

        permission = await permission_crud.get(
            db,
            role_permission.permission_id
        )

        users = await tenant_user_role_crud.get_by_fields(
            db,
            fields={'role_id': role_permission.role_id}
        )
        await self.create_notification(
            data={
                'tenant_id':tenant_id,
                'user_id':user_id,
                'title':'Access Update',
                'message': "You have update permissions for role"
            })
        message = f"A permission '{permission.name}' has been " + ("granted" if role_permission.is_active else "revoked")
        for user in users:     
            await self.create_notification(
                data={
                    'tenant_id':tenant_id,
                    'user_id':user.user_id,
                    'title':'Access Update',
                    'message': message
                })
    
    async def notify_end_sprint(self, db: AsyncSession, sprint: Sprint, tenant_id: str, user_id: str):
        
        await notify.create_notification(
            data={
                'tenant_id':tenant_id,
                'user_id':str(user_id),
                'title': f"Sprint completed: {sprint.sprint_number}",
                'message': f"You have completed the sprint {sprint.sprint_number} named {sprint.name}"
            }
        )
        members = await project_member_crud.get_by_fields(
            db,
            fields={'project_id': sprint.project_id, 'is_removed': False}
        )
        message = f"The sprint {sprint.sprint_number} has been ended. Please move your open issues to appropriate state."
        for member in members:
            staff = await cache_utils.get_or_set_staff(db, member.staff_id, tenant_id)
            if staff:
                staff_user_id = staff['user_id']
                staff_id = staff['staff_id']
                staff_email = staff['email']
            else:
                staff = await staff_crud.get(db, member.staff_id)
                staff_user_id = staff.user_id
                staff_id = staff.id
                staff_email = staff.email
            
            notification = await self.create_notification(
                data={
                    'tenant_id':tenant_id,
                    'user_id':staff_user_id,
                    'title':'Sprint Ended',
                    'message': message
                    })
            await self.create_notification(
                data={
                    'tenant_id':tenant_id,
                    'user_id':staff_user_id,
                    'title':'New Sprint',
                    'message': f'A new sprint {sprint.sprint_number + 1} has been started.'
                    })
            assigned_tasks = await task_assignee_crud.get_by_fields(
                db,
                fields={'staff_id': staff_id, 'is_primary': True}
            )
            tickets = []
            for assignes_task in assigned_tasks:
                task = await task_crud.get(db, assignes_task.task_id)
                if not task.completed_at:
                    tickets.append(f"{task.ticket_code}-{task.ticket_number}")
            if len(tickets) > 0:
                await self.enqueue_notification_job(
                    channel='email',
                    tenant_id=tenant_id,
                    notification_id=notification.id,
                    payload={
                        'to': staff_email,
                        'subject': 'Sprint Closure - Action Required on Open Tickets',
                        'body': SPRINT_END.format(tickets=', '.join(tickets))
                    }
                )
            
    async def notify_staff(self, staff: StaffProfile, department: Department, designation: Designation, tenant_id: str, user_id: str):
        
        notification = await notify.create_notification(     
        data={
            'tenant_id':tenant_id,
            'user_id':str(staff.user_id),
            'title': f"Welcome to the company, {staff.first_name}!",
            'message': f"Your staff profile has been created successfully. Your employee code is {staff.employee_code}."
            }
        )
        await notify.create_notification(
            data={
                'tenant_id':tenant_id,
                'user_id':str(user_id),
                'title': "New Staff",
                'message': f"You have added a new staff {staff.first_name} {staff.last_name}"
            }
        )
        await self.enqueue_notification_job(
            tenant_id=tenant_id,
            notification_id=notification.id,
            channel='email',
            payload={
                'to': staff.email,
                'subject': 'Welcome to the company!',
                'body': STAFF_JOINING.format(
                    name=staff.first_name,
                    id=staff.employee_code,
                    designation=designation.name,
                    department=department.name
                )
            }
        )
        
    async def notify_staff_remove(self, staff: StaffProfile, tenant_id: str, user_id: str):
        
        notification = await notify.create_notification(
            data={
                'tenant_id':tenant_id,
                'user_id':str(user_id),
                'title': "Staff Removed",
                'message': f"You have removed a staff {staff.first_name} {staff.last_name}"
            }
        )
    
        await notify.create_notification(
            data={
                'tenant_id':tenant_id,
                'user_id':str(staff.user_id),
                'title': "Staff profile deleted",
                'message': "Your staff profile has been deleted."
            }
        )
        await self.enqueue_notification_job(
            tenant_id=tenant_id,
            notification_id=notification.id,
            channel='email',
            payload={
                'to': staff.email,
                'subject': 'Employment Separation Notice',
                'body': STAFF_REMOVE.format(
                    name=staff.first_name
                )
            }
        )

    async def notify_task_assignment(self, db: AsyncSession, task: Task, task_assignees: List[TaskAssignee], tenant_id: str, user_id: str):

        staff_by = await staff_crud.get_by_field(db, field="user_id", value=user_id)
        for assignee in task_assignees:
            staff = await cache_utils.get_or_set_staff(db, assignee.staff_id, tenant_id)
            if staff:
                staff_user_id = staff['user_id']
                staff_first_name = staff['first_name']
                staff_email = staff['email']
            else:
                staff = await staff_crud.get(db, assignee.staff_id)
                staff_first_name = staff.first_name
                staff_user_id = staff.user_id
                staff_email = staff.email
            
            message = f'You have been assigned a task {task.ticket_code}-{task.ticket_number}'
            if assignee.is_primary:
                message += " as a collaborator"
            if user_id != staff_user_id and assignee.is_primary:
                message += f" by {staff_by.first_name} {staff_by.last_name}" 
            notification = await self.create_notification(
                data={
                    'tenant_id':tenant_id,
                    'user_id':staff_user_id,
                    'title':'Task Assigned',
                    'message':message
                }
            )
            if assignee.is_primary:
                await self.enqueue_notification_job(
                    tenant_id=tenant_id,
                    notification_id=notification.id,
                    channel='email',
                    payload={
                        'to': staff_email,
                        'subject': f'New Task Assigned to You - Ticket {task.ticket_code}-{task.ticket_number}',
                        'body': TASK_ASSIGNED.format(
                            name=staff_first_name,
                            ticket=f"{task.ticket_code}-{task.ticket_number}",
                            task_name=task.title,
                            description=task.description,
                            assigned_by=f"{staff_by.first_name} {staff_by.last_name}",
                            priority=task.priority
                        )
                    }
                )
            else:
                await self.enqueue_notification_job(
                    tenant_id=tenant_id,
                    notification_id=notification.id,
                    channel='email',
                    payload={
                        'to': staff_email,
                        'subject': f'You Have Been Added as a Collaborator on Ticket {task.ticket_code}-{task.ticket_number}',
                        'body': TASK_COLLABARATED.format(
                            name=staff_first_name,
                            ticket=f"{task.ticket_code}-{task.ticket_number}",
                            task_name=task.title,
                            description=task.description,
                            assigned_by=f"{staff_by.first_name} {staff_by.last_name}",
                            priority=task.priority
                        )
                    }
                )


    async def notify_state(self, db: AsyncSession, state: WorkflowState, tenant_id: str, user_id: str):
        project = await project_crud.get_by_field(db, field='workflow_id', value=state.workflow_id)
        members = await project_member_crud.get_by_fields(
            db,
            fields={'project_id': project.id, 'is_removed': False}
        )
        for member in members:
            staff = await cache_utils.get_or_set_staff(db, member.staff_id, tenant_id)
            if staff:
                staff_user_id = staff['user_id']
            else:
                staff = await staff_crud.get(db, member.staff_id)
                staff_user_id = staff.user_id
            
            await self.create_notification(
                data={
                    'tenant_id':tenant_id,
                    'user_id':staff_user_id,
                    'title': f"{project.code} | New State Added",
                    'message': f"A new state {state.name} has been added to the project {project.code}"
                }
            )
        
    async def notify_transition(self, db: AsyncSession, transition: WorkflowTransitions, tenant_id: str, user_id: str, is_deleted: bool= False):
        project = await project_crud.get_by_field(db, field='workflow_id', value=transition.workflow_id)
        members = await project_member_crud.get_by_fields(
            db,
            fields={'project_id': project.id, 'is_removed': False}
        )
        from_state = await workflow_state_crud.get(db, transition.from_state_id)
        to_state = await workflow_state_crud.get(db, transition.to_state_id)
        for member in members:
            staff = await cache_utils.get_or_set_staff(db, member.staff_id, tenant_id)
            if staff:
                staff_user_id = staff['user_id']
            else:
                staff = await staff_crud.get(db, member.staff_id)
                staff_user_id = staff.user_id
        
            await self.create_notification(
                data={
                    'tenant_id':tenant_id,
                    'user_id':staff_user_id,
                    'title': f"{project.code} | Transition Update",
                    'message': "A transition has been update now you "+ "can" if not is_deleted else "cannot" + f" move tasks from {from_state.name} to {to_state.name}"
                }
            )

    async def notify_project_member(self, db: AsyncSession, member: ProjectMember, tenant_id: str, user_id: str, is_removed: bool= False):
        project = await project_crud.get(db, member.project_id)
        staff = await cache_utils.get_or_set_staff(db, member.staff_id, tenant_id)
        if staff:
            staff_user_id = staff['user_id']
            staff_first_name = staff['first_name']
            staff_last_name = staff['last_name']
            staff_email = staff['email']
        else:
            staff = await staff_crud.get(db, member.staff_id)
            staff_user_id = staff.user_id
            staff_first_name = staff.first_name
            staff_last_name = staff.last_name
            staff_email = staff.email
            
        staff_by = await staff_crud.get_by_field(db, field="user_id", value=user_id)
        if is_removed:
            title_1 = f"Project member removed from project {project.name}"
            message_1 =  f"You have removed {staff_first_name} {staff_last_name} from project {project.name}."
            title_2 = f"Project member removed from project {project.name}"
            message_2 = f"You have been removed from project {project.name} by {staff_by.first_name} {staff_by.last_name}"
        else:
            title_1 = f"New project member in project {project.name}"
            message_1 = f"You have added {staff_first_name} {staff_last_name} to a project as {member.role}."
            title_2 = f"New project member in project {project.name}"
            message_2 = f"You have been added to a project as {member.role} by {staff_by.first_name} {staff_by.last_name}"
        await notify.create_notification(
            data={
                'tenant_id':str(tenant_id),
                'user_id':str(user_id),
                'title': title_1,
                'message': message_1
                }
            )
        
        notification = await notify.create_notification(
            data={
                'tenant_id':str(tenant_id),
                'user_id':str(staff_user_id),
                'title': title_2,
                'message': message_2
                }
            )
        
        if not is_removed:
            await self.enqueue_notification_job(
                tenant_id=tenant_id,
                notification_id=notification.id,
                channel='email',
                payload={
                    'to': staff_email,
                    'subject': f'Project Assignment Notification - {project.name}',
                    'body': ADD_MEMBER.format(
                        name=staff.first_name,
                        project=project.name,
                        project_code=project.code,
                        description=project.description,
                        priority=project.priority,
                        role=member.role,
                        added_by=f"{staff_by.first_name} {staff_by.last_name}",
                    )
                }
            )
            
    async def notify_task_deadline_alert(self, db:AsyncSession, tenant_id: str):
        
        tomorrow = date.today() + timedelta(days=1)
        tasks = await task_crud.get_multi(
            db,
            filters={'completed_at': None},
            extra_conditions=[Task.due_date == tomorrow]
        )
        for task in tasks:
            assignee = await task_assignee_crud.get_by_fields(
                db, 
                fields = {
                    'task_id': task.id,
                    'is_primary': True
                }
            )
            staff = await cache_utils.get_or_set_staff(db, assignee[0].staff_id, tenant_id)
            if staff:
                staff_user_id = staff['user_id']
                staff_first_name = staff['first_name']
                staff_email = staff['email']
            else:
                staff = await staff_crud.get(db, assignee[0].staff_id)
                staff_user_id = staff.user_id
                staff_first_name = staff.first_name
                staff_email = staff.email
            
            notification = await notify.create_notification(
                data={
                    'tenant_id':str(tenant_id),
                    'user_id':str(staff_user_id),
                    'title': "Incomplete Task",
                    'message': f"Your ticket {task.ticket_code}-{task.ticket_number} is incomplete. Last date is {task.due_date}"
                }
            )

            await self.enqueue_notification_job(
                tenant_id=tenant_id,
                notification_id=notification.id,
                channel='email',
                payload={
                    'to': staff_email,
                    'subject': f'Reminder: Incomplete Task Alert - Ticket {task.ticket_code}-{task.ticket_number}',
                    'body': TASK_INCOMPLETE_ALERT.format(
                        name=staff_first_name,
                        ticket = f'{task.ticket_code}-{task.ticket_number}',
                        task_name=task.title,
                        task_description=task.description,
                        due_date=task.due_date
                    )
                }
            )
            
    
        

notify = NotificationService()