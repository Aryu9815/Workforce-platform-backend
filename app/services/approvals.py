import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant.approvals import (
    ApprovalFlow,
    ApprovalStep,
    ApprovalInstance,
    ApprovalAssignment,
)
from app.services.crud import CRUDService


class ApprovalService:
    """
    ERP-grade approval engine.
    Fully aligned with CRUDService.
    No direct db.add().
    """

    def __init__(self):
        self.flow_crud = CRUDService(ApprovalFlow)
        self.step_crud = CRUDService(ApprovalStep)
        self.instance_crud = CRUDService(ApprovalInstance)
        self.assignment_crud = CRUDService(ApprovalAssignment)

    # ============================================================
    # FLOW CREATION
    # ============================================================

    async def create_flow(
        self,
        db: AsyncSession,
        *,
        name: str,
        entity_type: str,
        user_id: str,
        description: Optional[str] = None,
        is_default: bool = False,
        conditions: Optional[dict] = None,
    ) -> ApprovalFlow:

        flow = await self.flow_crud.create(
            db,
            obj_in={
                "name": name,
                "entity_type": entity_type,
                "description": description,
                "is_default": is_default,
                "conditions": conditions,
                "updated_by": user_id,
            },
            user_id=user_id,
        )

        return flow

    async def create_step(
        self,
        db: AsyncSession,
        *,
        flow_id: UUID,
        name: str,
        order_index: int,
        approver_type: str,
        user_id: str,
        approver_id: Optional[UUID] = None,
        approver_role_id: Optional[UUID] = None,
        is_parallel: bool = False,
        minimum_approvals: int = 1,
        sla_hours: Optional[int] = None,
        escalation_step_id: Optional[UUID] = None,
        conditions: Optional[dict] = None,
    ) -> ApprovalStep:

        step = await self.step_crud.create(
            db,
            obj_in={
                "flow_id": flow_id,
                "name": name,
                "order_index": order_index,
                "approver_type": approver_type,
                "approver_id": approver_id,
                "approver_role_id": approver_role_id,
                "is_parallel": is_parallel,
                "minimum_approvals": minimum_approvals,
                "sla_hours": sla_hours,
                "escalation_step_id": escalation_step_id,
                "conditions": conditions,
                "updated_by": user_id,
            },
            user_id=user_id,
        )

        return step

    # ============================================================
    # START APPROVAL
    # ============================================================

    async def start_approval(
        self,
        db: AsyncSession,
        *,
        flow_id: UUID,
        entity_type: str,
        entity_id: UUID,
        requester_id: UUID,
        user_id: str,
    ) -> ApprovalInstance:

        first_step = await self._get_first_step(db, flow_id)

        if not first_step:
            raise Exception("Approval flow has no steps")

        instance = await self.instance_crud.create(
            db,
            obj_in={
                "flow_id": flow_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "requester_id": requester_id,
                "status": "in_progress",
                "current_step_id": first_step.id,
                "started_at": datetime.now(timezone.utc),
                "updated_by": user_id,
            },
            user_id=user_id,
        )

        await self._assign_step(db, instance, first_step, user_id)

        return instance

    # ============================================================
    # PROCESS DECISION
    # ============================================================

    async def process_decision(
        self,
        db: AsyncSession,
        *,
        assignment_id: UUID,
        approver_id: UUID,
        decision: str,  # approved / rejected
        comments: Optional[str],
        user_id: str,
    ) -> ApprovalInstance:

        assignment = await self.assignment_crud.get(db, assignment_id)

        if not assignment:
            raise Exception("Assignment not found")

        if assignment.approver_id != approver_id:
            raise Exception("Unauthorized")

        if assignment.status != "pending":
            raise Exception("Already decided")

        assignment = await self.assignment_crud.update(
            db,
            db_obj=assignment,
            obj_in={
                "status": decision,
                "comments": comments,
                "decided_at": datetime.now(timezone.utc),
            },
            updated_by=user_id,
        )

        instance = await self.instance_crud.get(db, assignment.instance_id)

        if decision == "rejected":
            await self.instance_crud.update(
                db,
                db_obj=instance,
                obj_in={
                    "status": "rejected",
                    "final_decision": "rejected",
                    "completed_at": datetime.now(timezone.utc),
                },
                updated_by=user_id,
            )
            return instance

        await self._evaluate_step_completion(
            db, instance, assignment.step_id, user_id
        )

        return instance

    # ============================================================
    # STEP COMPLETION CHECK
    # ============================================================

    async def _evaluate_step_completion(
        self,
        db: AsyncSession,
        instance: ApprovalInstance,
        step_id: UUID,
        user_id: str,
    ):

        step = await self.step_crud.get(db, step_id)

        approved_count = await self.assignment_crud.count(
            db,
            filters={
                "instance_id": instance.id,
                "step_id": step_id,
                "status": "approved",
            },
        )

        if approved_count < step.minimum_approvals:
            return

        next_step = await self._get_next_step(db, step)

        if not next_step:
            await self.instance_crud.update(
                db,
                db_obj=instance,
                obj_in={
                    "status": "approved",
                    "final_decision": "approved",
                    "completed_at": datetime.now(timezone.utc),
                },
                updated_by=user_id,
            )
            return

        await self.instance_crud.update(
            db,
            db_obj=instance,
            obj_in={"current_step_id": next_step.id},
            updated_by=user_id,
        )

        await self._assign_step(db, instance, next_step, user_id)

    # ============================================================
    # STEP ASSIGNMENT
    # ============================================================

    async def _assign_step(
        self,
        db: AsyncSession,
        instance: ApprovalInstance,
        step: ApprovalStep,
        user_id: str,
    ):

        due_at = None
        if step.sla_hours:
            due_at = datetime.now(timezone.utc) + timedelta(hours=step.sla_hours)

        # Direct user assignment only (role resolution external)
        if step.approver_id:
            await self.assignment_crud.create(
                db,
                obj_in={
                    "instance_id": instance.id,
                    "step_id": step.id,
                    "approver_id": step.approver_id,
                    "status": "pending",
                    "assigned_at": datetime.now(timezone.utc),
                    "due_at": due_at,
                    "updated_by": user_id,
                },
                user_id=user_id,
            )

    # ============================================================
    # STEP RETRIEVAL
    # ============================================================

    async def _get_first_step(
        self,
        db: AsyncSession,
        flow_id: UUID,
    ) -> Optional[ApprovalStep]:

        steps = await self.step_crud.get_multi(
            db,
            filters={"flow_id": flow_id},
            order_by="order_index",
        )

        return steps[0] if steps else None

    async def _get_next_step(
        self,
        db: AsyncSession,
        current_step: ApprovalStep,
    ) -> Optional[ApprovalStep]:

        steps = await self.step_crud.get_multi(
            db,
            filters={"flow_id": current_step.flow_id},
            order_by="order_index",
        )

        for step in steps:
            if step.order_index > current_step.order_index:
                return step

        return None

    # ============================================================
    # QUERY HELPERS
    # ============================================================

    async def get_pending_for_user(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> List[ApprovalAssignment]:

        return await self.assignment_crud.get_multi(
            db,
            filters={
                "approver_id": user_id,
                "status": "pending",
            },
        )
