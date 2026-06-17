"""Message queue client for RabbitMQ/Kafka integration"""

from typing import Optional, Dict, Any, Callable
import logging
import json
import aio_pika
from app.config import Config

logger = logging.getLogger(__name__)


class QueueClient:
    """Message queue client for RabbitMQ"""
    
    def __init__(self, config: Config):
        """
        Initialize queue client
        
        Args:
            config: Application configuration
        """
        self.config = config
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.RobustChannel] = None
        
    async def connect(self) -> None:
        """Establish RabbitMQ connection"""
        try:
            self._connection = await aio_pika.connect_robust(
                self.config.RABBITMQ_URL
            )
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=10)
            logger.info("RabbitMQ connection established")
        except Exception as e:
            logger.error(f"Failed to establish RabbitMQ connection: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close RabbitMQ connection"""
        if self._connection:
            await self._connection.close()
            logger.info("RabbitMQ connection closed")
    
    def _get_queue_name(self, queue_name: str) -> str:
        """
        Get full queue name with prefix
        
        Args:
            queue_name: Base queue name
            
        Returns:
            Full queue name with prefix
        """
        return f"{self.config.RABBITMQ_QUEUE_PREFIX}.{queue_name}"
    
    async def declare_queue(
        self, 
        queue_name: str, 
        durable: bool = True,
        arguments: Optional[Dict[str, Any]] = None
    ) -> aio_pika.Queue:
        """
        Declare a queue
        
        Args:
            queue_name: Queue name
            durable: Whether queue survives broker restart
            arguments: Additional queue arguments
            
        Returns:
            aio_pika.Queue instance
        """
        if not self._channel:
            await self.connect()
            
        full_queue_name = self._get_queue_name(queue_name)
        queue = await self._channel.declare_queue(
            full_queue_name,
            durable=durable,
            arguments=arguments
        )
        logger.info(f"Declared queue: {full_queue_name}")
        return queue
    
    async def publish_message(
        self, 
        queue_name: str, 
        message: Dict[str, Any],
        routing_key: Optional[str] = None,
        priority: Optional[int] = None
    ) -> bool:
        """
        Publish a message to a queue
        
        Args:
            queue_name: Target queue name
            message: Message payload (will be JSON encoded)
            routing_key: Optional routing key
            priority: Optional message priority (0-255)
            
        Returns:
            bool: True if published successfully
        """
        if not self._channel:
            await self.connect()
            
        try:
            full_queue_name = self._get_queue_name(queue_name)
            
            # Declare exchange (direct exchange by default)
            exchange = await self._channel.declare_exchange(
                full_queue_name,
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )
            
            # Declare queue
            queue = await self.declare_queue(queue_name)
            await queue.bind(exchange, routing_key=queue_name)
            
            # Create message
            message_body = json.dumps(message).encode()
            message_props = aio_pika.Message(
                message_body,
                priority=priority,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            
            # Publish
            await exchange.publish(
                message_props,
                routing_key=routing_key or queue_name
            )
            
            logger.debug(f"Published message to {full_queue_name}")
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
        """
        Consume messages from a queue
        
        Args:
            queue_name: Queue name to consume from
            callback: Async callback function to process messages
            auto_ack: Whether to auto-acknowledge messages
        """
        if not self._channel:
            await self.connect()
            
        try:
            full_queue_name = self._get_queue_name(queue_name)
            queue = await self.declare_queue(queue_name)
            
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    try:
                        # Parse message
                        message_body = json.loads(message.body.decode())
                        
                        # Call callback
                        await callback(message_body)
                        
                        # Acknowledge message
                        if not auto_ack:
                            await message.ack()
                            
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        if not auto_ack:
                            await message.nack(requeue=False)
                            
        except Exception as e:
            logger.error(f"Failed to consume messages from {queue_name}: {e}")
            raise
    
    async def get_queue_status(self, queue_name: str) -> Dict[str, Any]:
        """
        Get status information for a queue
        
        Args:
            queue_name: Queue name
            
        Returns:
            Dict with queue status info
        """
        if not self._channel:
            await self.connect()
            
        try:
            full_queue_name = self._get_queue_name(queue_name)
            queue = await self.declare_queue(queue_name)
            
            # Get queue info
            queue_info = {
                "queue_name": full_queue_name,
                "message_count": queue.message_count,
                "consumer_count": queue.consumer_count
            }
            
            return queue_info
            
        except Exception as e:
            logger.error(f"Failed to get queue status for {queue_name}: {e}")
            return {
                "queue_name": queue_name,
                "error": str(e)
            }
    
    async def purge_queue(self, queue_name: str) -> int:
        """
        Purge all messages from a queue
        
        Args:
            queue_name: Queue name
            
        Returns:
            Number of messages purged
        """
        if not self._channel:
            await self.connect()
            
        try:
            full_queue_name = self._get_queue_name(queue_name)
            queue = await self.declare_queue(queue_name)
            result = await queue.purge()
            logger.info(f"Purged {result} messages from {full_queue_name}")
            return result
        except Exception as e:
            logger.error(f"Failed to purge queue {queue_name}: {e}")
            return 0
    
    # WMS-specific queue methods
    async def publish_order_event(
        self, 
        order_id: str, 
        event_type: str,
        payload: Dict[str, Any]
    ) -> bool:
        """
        Publish an order-related event
        
        Args:
            order_id: Order ID
            event_type: Event type (e.g., "order_created", "order_picked")
            payload: Event payload
            
        Returns:
            bool: True if published successfully
        """
        message = {
            "event_type": event_type,
            "order_id": order_id,
            "timestamp": payload.get("timestamp"),
            "data": payload
        }
        return await self.publish_message("order.events", message)
    
    async def publish_inventory_event(
        self, 
        sku_code: str, 
        event_type: str,
        payload: Dict[str, Any]
    ) -> bool:
        """
        Publish an inventory-related event
        
        Args:
            sku_code: SKU code
            event_type: Event type (e.g., "stock_updated", "stock_adjusted")
            payload: Event payload
            
        Returns:
            bool: True if published successfully
        """
        message = {
            "event_type": event_type,
            "sku_code": sku_code,
            "timestamp": payload.get("timestamp"),
            "data": payload
        }
        return await self.publish_message("inventory.events", message)
    
    async def get_order_queue_backlog(self) -> Dict[str, Any]:
        """
        Get backlog status for order processing queues
        
        Returns:
            Dict with queue backlog information
        """
        order_queues = [
            "order.process",
            "order.pick",
            "order.pack",
            "order.ship"
        ]
        
        backlog_info = {}
        for queue_name in order_queues:
            status = await self.get_queue_status(queue_name)
            backlog_info[queue_name] = status
            
        return backlog_info
