# Error Handling Guide

## Error Codes
VALIDATION_ERROR: Invalid input
NOT_FOUND: Resource missing  
DATABASE_ERROR: DB operation failed
REDIS_ERROR: Redis operation failed
LOCK_ACQUISITION_FAILED: Cannot get lock
INSUFFICIENT_STOCK: Not enough inventory
INSUFFICIENT_CAPACITY: No storage space
QUEUE_ERROR: Message queue failed

## Error Response Format
{"success": false, "error": "message", "error_code": "CODE"}

## Handling Strategy
1. Check error_code for specific handling
2. Retry transient errors (DB, Redis, Queue)
3. Validate inputs before retry
4. Log errors for debugging
5. Alert on critical errors
