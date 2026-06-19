"""Event-driven architecture: Event bus, event sourcing, CQRS"""

import asyncio
import json
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from abc import ABC, abstractmethod
from enum import Enum


class EventType(Enum):
    """Event types"""
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    INVENTORY_UPDATED = "inventory.updated"
    SHIPMENT_CREATED = "shipment.created"
    SHIPMENT_DELIVERED = "shipment.delivered"


class Event:
    """Base event class"""
    
    def __init__(
        self,
        event_type: EventType,
        payload: Dict[str, Any],
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.event_id = event_id or str(datetime.utcnow().timestamp())
        self.event_type = event_type
        self.payload = payload
        self.timestamp = timestamp or datetime.utcnow()
        self.version = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary"""
        return cls(
            event_type=EventType(data["event_type"]),
            payload=data["payload"],
            event_id=data["event_id"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


class EventBus:
    """Event bus for publishing and subscribing to events"""
    
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.event_history: List[Event] = []
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe from event type"""
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(handler)
    
    async def publish(self, event: Event):
        """Publish event to subscribers"""
        self.event_history.append(event)
        
        if event.event_type in self.subscribers:
            tasks = [handler(event) for handler in self.subscribers[event.event_type]]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_event_history(self, event_type: Optional[EventType] = None) -> List[Event]:
        """Get event history"""
        if event_type:
            return [e for e in self.event_history if e.event_type == event_type]
        return self.event_history.copy()


class EventStore:
    """Event store for event sourcing"""
    
    def __init__(self):
        self.events: Dict[str, List[Event]] = {}  # aggregate_id -> events
    
    async def save_event(self, aggregate_id: str, event: Event):
        """Save event to store"""
        if aggregate_id not in self.events:
            self.events[aggregate_id] = []
        self.events[aggregate_id].append(event)
    
    async def get_events(self, aggregate_id: str) -> List[Event]:
        """Get events for aggregate"""
        return self.events.get(aggregate_id, [])
    
    async def replay_events(self, aggregate_id: str) -> List[Event]:
        """Replay events for aggregate"""
        return await self.get_events(aggregate_id)


class Command:
    """Base command class"""
    
    def __init__(self, command_type: str, payload: Dict[str, Any]):
        self.command_type = command_type
        self.payload = payload
        self.timestamp = datetime.utcnow()


class Query:
    """Base query class"""
    
    def __init__(self, query_type: str, parameters: Dict[str, Any]):
        self.query_type = query_type
        self.parameters = parameters
        self.timestamp = datetime.utcnow()


class CQRSHandler:
    """CQRS pattern handler"""
    
    def __init__(self):
        self.command_handlers: Dict[str, Callable] = {}
        self.query_handlers: Dict[str, Callable] = {}
    
    def register_command_handler(self, command_type: str, handler: Callable):
        """Register command handler"""
        self.command_handlers[command_type] = handler
    
    def register_query_handler(self, query_type: str, handler: Callable):
        """Register query handler"""
        self.query_handlers[query_type] = handler
    
    async def execute_command(self, command: Command) -> Any:
        """Execute command"""
        if command.command_type not in self.command_handlers:
            raise ValueError(f"No handler for command: {command.command_type}")
        
        handler = self.command_handlers[command.command_type]
        return await handler(command)
    
    async def execute_query(self, query: Query) -> Any:
        """Execute query"""
        if query.query_type not in self.query_handlers:
            raise ValueError(f"No handler for query: {query.query_type}")
        
        handler = self.query_handlers[query.query_type]
        return await handler(query)


class EventReplay:
    """Event replay capability"""
    
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
    
    async def replay_to_state(self, aggregate_id: str, target_version: int) -> List[Event]:
        """Replay events to specific version"""
        events = await self.event_store.get_events(aggregate_id)
        return events[:target_version]
    
    async def replay_from_timestamp(self, aggregate_id: str, timestamp: datetime) -> List[Event]:
        """Replay events from specific timestamp"""
        events = await self.event_store.get_events(aggregate_id)
        return [e for e in events if e.timestamp >= timestamp]


class EventVersioning:
    """Event versioning for schema evolution"""
    
    def __init__(self):
        self.event_versions: Dict[str, Dict[str, Any]] = {}
    
    def register_event_version(self, event_type: str, version: str, schema: Dict[str, Any]):
        """Register event version schema"""
        key = f"{event_type}:{version}"
        self.event_versions[key] = schema
    
    def get_event_schema(self, event_type: str, version: str) -> Optional[Dict[str, Any]]:
        """Get event schema for version"""
        key = f"{event_type}:{version}"
        return self.event_versions.get(key)
    
    def migrate_event(self, event: Event, target_version: str) -> Event:
        """Migrate event to target version"""
        # Implementation would transform event payload to target version
        return event


# Singleton instances
event_bus = EventBus()
event_store = EventStore()
cqrs_handler = CQRSHandler()
event_replay = EventReplay(event_store)
event_versioning = EventVersioning()
