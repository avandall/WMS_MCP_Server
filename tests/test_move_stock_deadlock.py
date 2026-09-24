"""Concurrency and deadlock unit tests for move_stock_between_locations (TASK-049 / TECH-BUG-01/02).

Acceptance Criteria:
1. Lexicographical lock ordering: keys_to_lock = sorted([lock_key_from, lock_key_to]).
2. Exact lock_value preserved on release in normal and exception flows (no str(uuid.uuid4()) leak).
3. Concurrency simulation: 2 workers running 200 cross-transfers between LOC-A and LOC-B simultaneously:
   100% complete successfully with zero deadlocks and zero timeouts.
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock

from app.tools.transactions.move_stock_between_locations import MoveStockBetweenLocations
from app.clients.redis_client import RedisClient
from app.config import Config


class InMemoryLockRedis:
    """Thread-safe and async-safe in-memory Redis lock simulator with realistic contention."""

    def __init__(self):
        self.locks: dict[str, str] = {}
        self.lock_history: list[tuple[str, str, str]] = []  # (action, key, value)
        self._mutex = asyncio.Lock()

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def acquire_lock(self, lock_key: str, lock_value: str, expire: int = 30) -> bool:
        async with self._mutex:
            if lock_key in self.locks:
                return False
            self.locks[lock_key] = lock_value
            self.lock_history.append(("ACQUIRE", lock_key, lock_value))
            return True

    async def release_lock(self, lock_key: str, lock_value: str) -> bool:
        async with self._mutex:
            self.lock_history.append(("RELEASE", lock_key, lock_value))
            if self.locks.get(lock_key) == lock_value:
                del self.locks[lock_key]
                return True
            return False

    async def acquire_multiple_locks(
        self,
        keys: list[str],
        lock_value: str,
        expire: int = 30,
        timeout: float = 10.0,
        retry_interval: float = 0.005,
    ) -> bool:
        sorted_keys = sorted(list(set(keys)))
        start_time = time.monotonic()

        while (time.monotonic() - start_time) < timeout:
            acquired = []
            all_ok = True
            for key in sorted_keys:
                ok = await self.acquire_lock(key, lock_value, expire=expire)
                if ok:
                    acquired.append(key)
                else:
                    all_ok = False
                    break

            if all_ok:
                return True

            # Rollback any locks acquired during this attempt
            for key in acquired:
                await self.release_lock(key, lock_value)
            acquired.clear()

            await asyncio.sleep(retry_interval)

        return False

    async def release_multiple_locks(self, keys: list[str], lock_value: str) -> None:
        for key in keys:
            await self.release_lock(key, lock_value)

    async def cache_delete(self, key: str) -> bool:
        return True


class InMemoryStockDatabase:
    """Mock database tracking location inventory with concurrency synchronization."""

    def __init__(self, sku_code: str, loc_a_qty: int = 1000, loc_b_qty: int = 1000):
        self.sku_code = sku_code
        self.stocks = {
            "LOC-A": loc_a_qty,
            "LOC-B": loc_b_qty,
        }
        self._mutex = asyncio.Lock()

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def get_stock_info(self, sku_code: str, warehouse_id=None):
        async with self._mutex:
            return [
                {"location_code": "LOC-A", "available_qty": self.stocks["LOC-A"]},
                {"location_code": "LOC-B", "available_qty": self.stocks["LOC-B"]},
            ]

    async def execute_transaction(self, queries: list[dict]) -> bool:
        async with self._mutex:
            for q in queries:
                params = q.get("params", [])
                qty = params[0]
                loc = params[2]
                if "physical_qty - $1" in q.get("query", ""):
                    self.stocks[loc] -= qty
                elif "physical_qty + $1" in q.get("query", ""):
                    self.stocks[loc] += qty
            # Small async yield to simulate network/database latency
            await asyncio.sleep(0.001)
            return True


@pytest.mark.asyncio
async def test_concurrent_cross_transfers_no_deadlock(test_config):
    """
    Acceptance Criteria:
    Mô phỏng 2 workers chạy đồng thời 200 lượt chuyển hàng chéo giữa LOC-A và LOC-B:
    Worker 1: LOC-A -> LOC-B (100 operations)
    Worker 2: LOC-B -> LOC-A (100 operations)
    100% các lượt chuyển hàng hoàn thành thành công mà không có trường hợp nào bị Deadlock hay Timeout.
    """
    redis_sim = InMemoryLockRedis()
    db_sim = InMemoryStockDatabase(sku_code="SKU-DEADLOCK-TEST", loc_a_qty=1000, loc_b_qty=1000)

    # Worker 1 transfers LOC-A -> LOC-B
    async def worker_1_task(task_id: int):
        tool = MoveStockBetweenLocations(test_config)
        tool.redis = redis_sim
        tool.db = db_sim
        res = await tool.execute(
            sku_code="SKU-DEADLOCK-TEST",
            from_location="LOC-A",
            to_location="LOC-B",
            quantity=1,
        )
        return res

    # Worker 2 transfers LOC-B -> LOC-A
    async def worker_2_task(task_id: int):
        tool = MoveStockBetweenLocations(test_config)
        tool.redis = redis_sim
        tool.db = db_sim
        res = await tool.execute(
            sku_code="SKU-DEADLOCK-TEST",
            from_location="LOC-B",
            to_location="LOC-A",
            quantity=1,
        )
        return res

    # Create 200 interlaced tasks (100 A->B and 100 B->A)
    tasks = []
    for i in range(100):
        tasks.append(worker_1_task(i))
        tasks.append(worker_2_task(i))

    start_time = time.monotonic()
    results = await asyncio.gather(*tasks)
    total_time = time.monotonic() - start_time

    # 1. 100% success rate verification
    success_count = sum(1 for r in results if r.success)
    assert success_count == 200, f"Expected 200 successful transfers, got {success_count}. Errors: {[r.error for r in results if not r.success]}"

    # 2. Check no locks remain leaked or frozen in Redis
    assert len(redis_sim.locks) == 0, f"Leaked locks remaining: {redis_sim.locks}"

    # 3. Final stock balances should be unchanged (100 moved A->B and 100 moved B->A)
    assert db_sim.stocks["LOC-A"] == 1000
    assert db_sim.stocks["LOC-B"] == 1000
    assert total_time < 10.0, f"Execution took too long ({total_time:.2f}s), possible lock congestion"


@pytest.mark.asyncio
async def test_lexicographical_lock_ordering(test_config):
    """
    Acceptance Criteria:
    Bắt buộc dùng keys_to_lock = sorted([lock_key_from, lock_key_to]).
    Verifies that whether transfer is A->B or B->A, the locks are acquired in the exact same sorted order.
    """
    redis_sim = InMemoryLockRedis()
    db_sim = InMemoryStockDatabase(sku_code="SKU-ORDER-TEST")

    tool = MoveStockBetweenLocations(test_config)
    tool.redis = redis_sim
    tool.db = db_sim

    # Transfer B -> A
    res = await tool.execute(
        sku_code="SKU-ORDER-TEST",
        from_location="LOC-B",
        to_location="LOC-A",
        quantity=5,
    )
    assert res.success is True

    # Inspect acquisition history: LOC-A must have been acquired before LOC-B!
    acquire_history = [item for item in redis_sim.lock_history if item[0] == "ACQUIRE"]
    assert len(acquire_history) >= 2

    # First acquired key should be LOC-A because 'LOC-A' < 'LOC-B' alphabetically
    assert "LOC-A" in acquire_history[0][1]
    assert "LOC-B" in acquire_history[1][1]


@pytest.mark.asyncio
async def test_lock_token_preserved_on_exception_no_uuid_leak(test_config):
    """
    Acceptance Criteria (TECH-BUG-02):
    Lưu trữ biến lock_value an toàn; trong khối except, truyền chính xác lock_value
    vào release_lock (cấm truyền str(uuid.uuid4()) mới).
    """
    redis_sim = InMemoryLockRedis()

    class FailingDatabaseClient:
        async def connect(self):
            pass

        async def disconnect(self):
            pass

        async def get_stock_info(self, *args, **kwargs):
            raise RuntimeError("Database connection suddenly dropped!")

    tool = MoveStockBetweenLocations(test_config)
    tool.redis = redis_sim
    tool.db = FailingDatabaseClient()

    result = await tool.execute(
        sku_code="SKU-LEAK-TEST",
        from_location="LOC-A",
        to_location="LOC-B",
        quantity=1,
    )

    # Tool should return handled error
    assert result.success is False
    assert "Database connection suddenly dropped" in (result.error or "")

    # CRITICAL: Verify that the locks acquired before the crash were cleanly released
    # and no lock was left frozen with an unmatched token!
    assert len(redis_sim.locks) == 0, f"Locks were leaked due to token mismatch! Remaining locks: {redis_sim.locks}"

    # Verify that the token in the RELEASE call matches the token in the ACQUIRE call
    acquire_tokens = {k: v for act, k, v in redis_sim.lock_history if act == "ACQUIRE"}
    release_tokens = {k: v for act, k, v in redis_sim.lock_history if act == "RELEASE"}

    for key, acq_tok in acquire_tokens.items():
        assert key in release_tokens, f"Key {key} was acquired but never released"
        assert release_tokens[key] == acq_tok, (
            f"Token mismatch for key {key}! Acquired with {acq_tok} but released with {release_tokens[key]}"
        )
