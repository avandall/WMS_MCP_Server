"""Configuration management for WMS MCP Server"""

from typing import List, Optional
from pydantic import BaseSettings, Field
from pydantic_settings import BaseSettings as PydanticBaseSettings
import os


class Config(PydanticBaseSettings):
    """Application configuration using environment variables"""
    
    # Application
    APP_NAME: str = Field(default="wms-mcp-server", description="Application name")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Server
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://wms:wms@localhost:5432/wms",
        description="Database connection URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow connections")
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_POOL_SIZE: int = Field(default=10, description="Redis connection pool size")
    
    # Message Queue (RabbitMQ)
    RABBITMQ_URL: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL"
    )
    RABBITMQ_QUEUE_PREFIX: str = Field(default="wms", description="Queue name prefix")
    
    # Tool Configuration
    ENABLE_TOOLS: List[str] = Field(
        default_factory=list,
        description="List of enabled tools (empty = all tools enabled)"
    )
    DISABLE_TOOLS: List[str] = Field(
        default_factory=list,
        description="List of disabled tools"
    )
    
    # API Keys (for external services)
    SHIPPING_API_KEY: Optional[str] = Field(default=None, description="Shipping API key")
    SHIPPING_API_SECRET: Optional[str] = Field(default=None, description="Shipping API secret")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_RPS: int = Field(default=100, description="Requests per second limit")
    RATE_LIMIT_BURST: int = Field(default=200, description="Burst limit")
    
    # Caching
    CACHE_ENABLED: bool = Field(default=True, description="Enable caching")
    CACHE_TTL_SECONDS: int = Field(default=300, description="Default cache TTL in seconds")
    
    # Security
    SECRET_KEY: str = Field(default="change-me-in-production", description="Secret key for signing")
    API_KEY_REQUIRED: bool = Field(default=False, description="Require API key for access")
    VALID_API_KEYS: List[str] = Field(default_factory=list, description="Valid API keys")
    
    # Monitoring
    METRICS_ENABLED: bool = Field(default=True, description="Enable metrics collection")
    METRICS_PORT: int = Field(default=9090, description="Metrics port")
    
    # gRPC Configuration (for WMS Core integration)
    IDENTITY_GRPC_ADDR: str = Field(default="identity-service:50051", description="Identity service gRPC address")
    CUSTOMER_GRPC_ADDR: str = Field(default="customer-service:50052", description="Customer service gRPC address")
    PRODUCT_GRPC_ADDR: str = Field(default="product-service:50053", description="Product service gRPC address")
    WAREHOUSE_GRPC_ADDR: str = Field(default="warehouse-service:50054", description="Warehouse service gRPC address")
    INVENTORY_GRPC_ADDR: str = Field(default="inventory-service:50055", description="Inventory service gRPC address")
    DOCUMENTS_GRPC_ADDR: str = Field(default="documents-service:50056", description="Documents service gRPC address")
    AUDIT_GRPC_ADDR: str = Field(default="audit-service:50057", description="Audit service gRPC address")
    REPORTING_GRPC_ADDR: str = Field(default="reporting-service:50058", description="Reporting service gRPC address")
    AI_GRPC_ADDR: str = Field(default="ai-service:50059", description="AI service gRPC address")
    
    GRPC_TIMEOUT_FAST: int = Field(default=5, description="Fast gRPC timeout in seconds")
    GRPC_TIMEOUT_DEFAULT: int = Field(default=10, description="Default gRPC timeout in seconds")
    GRPC_TIMEOUT_SLOW: int = Field(default=30, description="Slow gRPC timeout in seconds")
    GRPC_TIMEOUT_AI: int = Field(default=60, description="AI gRPC timeout in seconds")
    GRPC_RETRY_ATTEMPTS: int = Field(default=2, description="gRPC retry attempts")
    GRPC_RETRY_BACKOFF_SECONDS: float = Field(default=0.05, description="gRPC retry backoff")
    
    GRPC_CLIENT_TLS_ENABLED: bool = Field(default=False, description="Enable gRPC TLS")
    GRPC_CLIENT_ROOT_CERT_FILE: str = Field(default="", description="gRPC root cert file")
    GRPC_CLIENT_CERT_FILE: str = Field(default="", description="gRPC client cert file")
    GRPC_CLIENT_KEY_FILE: str = Field(default="", description="gRPC client key file")
    
    # Circuit Breaker
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(default=5, description="Circuit breaker failure threshold")
    CIRCUIT_BREAKER_RECOVERY_SECONDS: int = Field(default=15, description="Circuit breaker recovery time")
    
    # Event Bus
    EVENT_BUS_URL: str = Field(default="redis://event-bus:6379/0", description="Event bus Redis URL")
    EVENT_STREAM: str = Field(default="wms.events", description="Event stream name")
    EVENTS_ENABLED: bool = Field(default=True, description="Enable event publishing")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """
        Check if a tool is enabled based on configuration
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            bool: True if tool is enabled
        """
        # If explicitly disabled
        if tool_name in self.DISABLE_TOOLS:
            return False
            
        # If enable list is empty, all tools are enabled
        if not self.ENABLE_TOOLS:
            return True
            
        # If enable list is not empty, tool must be in it
        return tool_name in self.ENABLE_TOOLS


def get_config() -> Config:
    """
    Get configuration instance
    
    Returns:
        Config instance
    """
    return Config()
