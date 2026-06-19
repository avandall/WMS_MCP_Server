"""Resilience patterns: Circuit breaker and retry logic"""

import asyncio
import time
from typing import Callable, Optional, Any, Dict
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker pattern for service resilience"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Exception = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self.last_failure_time is None:
            return True
        
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:  # Success threshold
                self.state = CircuitState.CLOSED
                self.success_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time
        }
    
    def reset(self):
        """Reset circuit breaker to closed state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None


class RetryPolicy:
    """Retry policy with exponential backoff"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        delay = min(
            self.initial_delay * (self.exponential_base ** (attempt - 1)),
            self.max_delay
        )
        
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random())
        
        return delay


class RetryHandler:
    """Retry handler with exponential backoff"""
    
    def __init__(self, policy: Optional[RetryPolicy] = None):
        self.policy = policy or RetryPolicy()
    
    async def execute(
        self,
        func: Callable,
        *args,
        expected_exception: Exception = Exception,
        **kwargs
    ) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except expected_exception as e:
                last_exception = e
                
                if attempt == self.policy.max_attempts:
                    raise e
                
                delay = self.policy.calculate_delay(attempt)
                await asyncio.sleep(delay)
        
        raise last_exception


class ServiceMeshIntegration:
    """Service mesh integration for advanced routing and observability"""
    
    def __init__(self):
        self.service_mesh_enabled = False
        self.mesh_config = {}
    
    def enable_service_mesh(self, config: Dict[str, Any]):
        """Enable service mesh integration"""
        self.service_mesh_enabled = True
        self.mesh_config = config
    
    def get_mesh_config(self) -> Dict[str, Any]:
        """Get service mesh configuration"""
        return self.mesh_config.copy()
    
    def is_enabled(self) -> bool:
        """Check if service mesh is enabled"""
        return self.service_mesh_enabled


# Singleton instances
circuit_breaker = CircuitBreaker()
retry_handler = RetryHandler()
service_mesh = ServiceMeshIntegration()
