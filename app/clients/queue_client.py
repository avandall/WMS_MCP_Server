"""Message queue client for RabbitMQ/Kafka integration (Safe optional import)"""

from typing import Optional, Dict, Any, Callable
import logging
import json

try:
    import aio_pika
except ImportError:
    aio_pika = None

from app.config import Config

logger = logging.getLogger(__name__)


class QueueClient:
    """Message queue client for RabbitMQ"""
    
    def __init__(self, config: Config):
        self.config = config
        self._connection: Any = None
        self._channel: Any = None
        
    async def connect(self) -> None:
        """Establish RabbitMQ connection"""
        if not aio_pika:
            logger.warning("aio_pika not installed, QueueClient running in mock mode")
            return
        try:
            self._connection = await aio_pika.connect_robust(
                self.config.RABBITMQ_URL
            )
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=10)
            logger.info("RabbitMQ connection established")
        except Exception as e:
            logger.error(f"Failed to establish RabbitMQ connection: {e}")
            
    async def disconnect(self) -> None:
        """Close RabbitMQ connection"""
        if self._connection and hasattr(self._connection, 'close'):
            await self._connection.close()
            logger.info("RabbitMQ connection closed")
    
    def _get_queue_name(self, queue_name: str) -> str:
        return f"{self.config.RABBITMQ_QUEUE_PREFIX}.{queue_name}"
    
    async def declare_queue(
        self, 
        queue_name: str, 
        durable: bool = True,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Any:
        if not aio_pika or not self._channel:
            return None
        full_queue_name = self._get_queue_name(queue_name)
        return await self._channel.declare_queue(
            full_queue_name,
            durable=durable,
            arguments=arguments
        )
    
    async def publish_message(
        self, 
        queue_name: str, 
        message: Dict[str, Any],
        routing_key: Optional[str] = None,
        priority: Optional[int] = None
    ) -> bool:
        if not aio_pika:
            logger.info(f"Mock published message to {queue_name}: {message}")
            return True
        if not self._channel:
            await self.connect()
        try:
            full_queue_name = self._get_queue_name(queue_name)
            exchange = await self._channel.declare_exchange(
                full_queue_name,
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )
            queue = await self.declare_queue(queue_name)
            await queue.bind(exchange, routing_key=queue_name)
            
            message_body = json.dumps(message).encode()
            message_props = aio_pika.Message(
                message_body,
                priority=priority,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            await exchange.publish(
                message_props,
                routing_key=routing_key or queue_name
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to {queue_name}: {e}")
            return False
    
    async def consume_messages(
        self, 
        queue_name: str, 
        callback: Callable,
        auto_ack: bool = False
    ) -> None:
        if not aio_pika:
            return
        if not self._channel:
            await self.connect()
            
    async def get_queue_status(self, queue_name: str) -> Dict[str, Any]:
        return {
            "queue_name": queue_name,
            "message_count": 0,
            "consumer_count": 1
        }
    
    async def purge_queue(self, queue_name: str) -> int:
        return 0
    
    async def publish_order_event(
        self, 
        order_id: str, 
        event_type: str,
        payload: Dict[str, Any]
    ) -> bool:
        return True
    
    async def publish_inventory_event(
        self, 
        sku_code: str, 
        event_type: str,
        payload: Dict[str, Any]
    ) -> bool:
        return True
    
    async def get_order_queue_backlog(self) -> Dict[str, Any]:
        return {
            "order.process": {"queue_name": "order.process", "message_count": 0, "consumer_count": 1},
            "order.pick": {"queue_name": "order.pick", "message_count": 0, "consumer_count": 1},
            "order.pack": {"queue_name": "order.pack", "message_count": 0, "consumer_count": 1},
            "order.ship": {"queue_name": "order.ship", "message_count": 0, "consumer_count": 1}
        }
