"""Resource management for WMS MCP Server"""

import psutil
import gc
import asyncio
from typing import Dict, Any, Optional
from collections import defaultdict


class ResourceMonitor:
    """Resource monitoring for memory, CPU, and connections"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.max_history = 1000
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss": memory_info.rss / 1024 / 1024,  # MB
            "vms": memory_info.vms / 1024 / 1024,  # MB
            "percent": process.memory_percent()
        }
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage"""
        return psutil.cpu_percent(interval=0.1)
    
    def get_connection_count(self) -> int:
        """Get number of open connections"""
        process = psutil.Process()
        return len(process.connections())
    
    def record_metrics(self):
        """Record current metrics"""
        self.metrics["memory"].append(self.get_memory_usage())
        self.metrics["cpu"].append(self.get_cpu_usage())
        self.metrics["connections"].append(self.get_connection_count())
        
        # Keep only recent history
        for key in self.metrics:
            if len(self.metrics[key]) > self.max_history:
                self.metrics[key] = self.metrics[key][-self.max_history:]
    
    def get_average_metrics(self, samples: int = 100) -> Dict[str, Any]:
        """Get average metrics over recent samples"""
        avg_metrics = {}
        
        for key, values in self.metrics.items():
            recent_values = values[-samples:] if len(values) >= samples else values
            if recent_values:
                avg_metrics[key] = sum(recent_values) / len(recent_values)
        
        return avg_metrics


class MemoryOptimizer:
    """Memory optimization utilities"""
    
    def __init__(self):
        self.memory_threshold = 80  # 80% memory usage threshold
        self.auto_gc_enabled = True
    
    def check_memory_usage(self) -> bool:
        """Check if memory usage is above threshold"""
        process = psutil.Process()
        memory_percent = process.memory_percent()
        return memory_percent > self.memory_threshold
    
    def force_garbage_collection(self) -> Dict[str, Any]:
        """Force garbage collection"""
        before = self.get_memory_info()
        
        # Run garbage collection
        collected = gc.collect()
        
        after = self.get_memory_info()
        
        return {
            "collected_objects": collected,
            "memory_before": before,
            "memory_after": after,
            "memory_freed": before - after
        }
    
    def get_memory_info(self) -> float:
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def optimize_memory(self):
        """Optimize memory usage"""
        if self.auto_gc_enabled and self.check_memory_usage():
            return self.force_garbage_collection()
        return None


class ConnectionManager:
    """Connection manager with limits and cleanup"""
    
    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.active_connections = 0
        self.connection_pool = []
    
    async def acquire_connection(self) -> bool:
        """Acquire connection if limit not reached"""
        if self.active_connections >= self.max_connections:
            return False
        
        self.active_connections += 1
        return True
    
    def release_connection(self):
        """Release connection"""
        if self.active_connections > 0:
            self.active_connections -= 1
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status"""
        return {
            "active_connections": self.active_connections,
            "max_connections": self.max_connections,
            "available": self.max_connections - self.active_connections
        }
    
    async def cleanup_idle_connections(self, idle_timeout: int = 300):
        """Cleanup idle connections"""
        # Implementation would close connections idle for longer than timeout
        pass


class GracefulDegradation:
    """Graceful degradation under load"""
    
    def __init__(self):
        self.degradation_levels = {
            "normal": {"cpu_threshold": 70, "memory_threshold": 70},
            "degraded": {"cpu_threshold": 85, "memory_threshold": 85},
            "critical": {"cpu_threshold": 95, "memory_threshold": 95}
        }
        self.current_level = "normal"
    
    def check_degradation_level(self, cpu_usage: float, memory_usage: float) -> str:
        """Determine current degradation level"""
        if cpu_usage > self.degradation_levels["critical"]["cpu_threshold"] or \
           memory_usage > self.degradation_levels["critical"]["memory_threshold"]:
            self.current_level = "critical"
        elif cpu_usage > self.degradation_levels["degraded"]["cpu_threshold"] or \
             memory_usage > self.degradation_levels["degraded"]["memory_threshold"]:
            self.current_level = "degraded"
        else:
            self.current_level = "normal"
        
        return self.current_level
    
    def get_degraded_features(self) -> Dict[str, bool]:
        """Get features that should be disabled based on degradation level"""
        if self.current_level == "critical":
            return {
                "caching": False,
                "batch_operations": False,
                "async_processing": False,
                "logging": False
            }
        elif self.current_level == "degraded":
            return {
                "caching": True,
                "batch_operations": False,
                "async_processing": True,
                "logging": True
            }
        else:
            return {
                "caching": True,
                "batch_operations": True,
                "async_processing": True,
                "logging": True
            }
    
    def get_current_level(self) -> str:
        """Get current degradation level"""
        return self.current_level


class ResourceCleanup:
    """Resource cleanup utilities"""
    
    async def cleanup_resources(self):
        """Cleanup all resources"""
        # Force garbage collection
        gc.collect()
        
        # Close idle connections
        # Implementation would close idle connections
        
        # Clear caches
        # Implementation would clear caches
    
    async def periodic_cleanup(self, interval: int = 300):
        """Periodic resource cleanup"""
        while True:
            await asyncio.sleep(interval)
            await self.cleanup_resources()


# Singleton instances
resource_monitor = ResourceMonitor()
memory_optimizer = MemoryOptimizer()
connection_manager = ConnectionManager()
graceful_degradation = GracefulDegradation()
resource_cleanup = ResourceCleanup()
