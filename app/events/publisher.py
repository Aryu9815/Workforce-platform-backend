"""
Event publisher for domain events.
"""
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import asyncio
import logging
from dataclasses import dataclass
import json

from app.models.tenant import DomainEvent
from app.core.logging_config import get_logger

logger = get_logger("events")


class EventType(str, Enum):
    """System event types."""
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    
    # Tenant events
    TENANT_CREATED = "tenant.created"
    TENANT_UPDATED = "tenant.updated"
    
    # Staff events
    STAFF_CREATED = "staff.created"
    STAFF_UPDATED = "staff.updated"
    STAFF_DELETED = "staff.deleted"
    
    # Project events
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"
    
    # Task events
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_DELETED = "task.deleted"
    TASK_ASSIGNED = "task.assigned"
    TASK_COMPLETED = "task.completed"
    
    # Attendance events
    ATTENDANCE_CHECK_IN = "attendance.check_in"
    ATTENDANCE_CHECK_OUT = "attendance.check_out"
    LEAVE_REQUESTED = "leave.requested"
    LEAVE_APPROVED = "leave.approved"
    
    # Reimbursement events
    REIMBURSEMENT_SUBMITTED = "reimbursement.submitted"
    REIMBURSEMENT_APPROVED = "reimbursement.approved"
    REIMBURSEMENT_PAID = "reimbursement.paid"
    
    # Inventory events
    INVENTORY_LOW_STOCK = "inventory.low_stock"
    INVENTORY_TRANSACTION = "inventory.transaction"
    
    # Approval events
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_COMPLETED = "approval.completed"

    MEMBER_ADDED = "member.added"
    MEMBER_REMOVED = "member.removed"
    
@dataclass
class DomainEventData:
    """Domain event data structure."""
    event_type: EventType
    aggregate_type: str
    aggregate_id: str
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None


class EventPublisher:
    """Event publisher for domain events."""
    
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.event_history: List[DomainEventData] = []
        self.max_history = 1000
    
    def subscribe(
        self,
        event_type: EventType,
        handler: Callable
    ) -> None:
        """Subscribe a handler to an event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        self.subscribers[event_type].append(handler)
        logger.info(f"Handler subscribed to {event_type.value}")
    
    def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable
    ) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self.subscribers:
            self.subscribers[event_type] = [
                h for h in self.subscribers[event_type]
                if h != handler
            ]
    
    async def publish(
        self,
        event_type: EventType,
        aggregate_type: str,
        aggregate_id: str,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None
    ) -> DomainEventData:
        """Publish an event to all subscribers."""
        event_data = DomainEventData(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            metadata=metadata or {},
            correlation_id=correlation_id,
            causation_id=causation_id
        )
        
        # Add to history
        self.event_history.append(event_data)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        # Log event
        logger.info(
            f"Event published: {event_type.value} | "
            f"Aggregate: {aggregate_type}:{aggregate_id} | "
        )
        
        # Notify subscribers
        handlers = self.subscribers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event_data))
                else:
                    handler(event_data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type.value}: {e}")
        
        return event_data
    
    async def publish_many(
        self,
        events: List[DomainEventData]
    ) -> None:
        """Publish multiple events."""
        for event in events:
            await self.publish(
                event_type=event.event_type,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                payload=event.payload,
                metadata=event.metadata,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id
            )
    
    def get_subscribers(self, event_type: EventType) -> List[Callable]:
        """Get all subscribers for an event type."""
        return self.subscribers.get(event_type, [])
    
    def get_event_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[DomainEventData]:
        """Get event history, optionally filtered by type."""
        events = self.event_history
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events[-limit:]
    
    def clear_history(self) -> None:
        """Clear event history."""
        self.event_history.clear()


# Global event publisher instance
event_publisher = EventPublisher()


# Convenience function for publishing events
async def publish_event(
    event_type: EventType,
    aggregate_type: str,
    aggregate_id: str,
    payload: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None
) -> DomainEventData:
    """Publish a domain event."""
    return await event_publisher.publish(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload,
        metadata=metadata,
        correlation_id=correlation_id,
        causation_id=causation_id
    )


def subscribe_to_event(event_type: EventType):
    """Decorator for subscribing to events."""
    def decorator(func: Callable):
        event_publisher.subscribe(event_type, func)
        return func
    return decorator
