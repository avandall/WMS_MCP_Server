"""Async optimization for WMS MCP Server"""

import asyncio
from typing import Any, Callable, List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor


class AsyncOptimizer:
    """Async optimization utilities"""
    
    def __init__(self):
        self.max_concurrent_tasks = 100
        self.batch_size = 50
    
    async def execute_concurrent(self, tasks: List[Callable]) -> List[Any]:
        """Execute tasks concurrently with controlled concurrency"""
        semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        
        async def limited_execute(task):
            async with semaphore:
                return await task()
        
        results = await asyncio.gather(
            *[limited_execute(task) for task in tasks],
            return_exceptions=True
        )
        
        return results
    
    async def execute_batch(self, items: List[Any], processor: Callable) -> List[Any]:
        """Execute batch operations"""
        results = []
        
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_results = await asyncio.gather(
                *[processor(item) for item in batch],
                return_exceptions=True
            )
            results.extend(batch_results)
        
        return results
    
    async def execute_parallel_io(self, io_operations: List[Callable]) -> List[Any]:
        """Execute I/O operations in parallel"""
        return await asyncio.gather(*io_operations, return_exceptions=True)
    
    async def stream_results(self, generator: Callable) -> Any:
        """Stream results from async generator"""
        async for result in generator():
            yield result


class ThreadPoolManager:
    """Thread pool manager for CPU-bound tasks"""
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def run_in_thread(self, func: Callable, *args, **kwargs) -> Any:
        """Run CPU-bound function in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args, **kwargs)
    
    def shutdown(self):
        """Shutdown thread pool"""
        self.executor.shutdown(wait=True)


class AsyncBatchProcessor:
    """Async batch processor for bulk operations"""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
    
    async def process_batch(self, items: List[Any], processor: Callable) -> List[Any]:
        """Process items in batches"""
        results = []
        
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_results = await asyncio.gather(
                *[processor(item) for item in batch]
            )
            results.extend(batch_results)
        
        return results
    
    async def process_with_progress(self, items: List[Any], processor: Callable) -> Dict[str, Any]:
        """Process items with progress tracking"""
        total = len(items)
        processed = 0
        results = []
        
        for i in range(0, total, self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_results = await asyncio.gather(
                *[processor(item) for item in batch]
            )
            results.extend(batch_results)
            processed += len(batch)
            
            # Yield progress
            yield {
                "processed": processed,
                "total": total,
                "progress": (processed / total) * 100
            }
        
        return {"results": results, "total_processed": processed}


class AsyncStreamProcessor:
    """Async stream processor for large datasets"""
    
    async def process_stream(self, stream: Any, processor: Callable) -> List[Any]:
        """Process stream of data"""
        results = []
        
        async for item in stream:
            processed = await processor(item)
            results.append(processed)
        
        return results
    
    async def filter_stream(self, stream: Any, predicate: Callable) -> List[Any]:
        """Filter stream based on predicate"""
        results = []
        
        async for item in stream:
            if await predicate(item):
                results.append(item)
        
        return results


# Singleton instances
async_optimizer = AsyncOptimizer()
thread_pool_manager = ThreadPoolManager()
batch_processor = AsyncBatchProcessor()
stream_processor = AsyncStreamProcessor()
