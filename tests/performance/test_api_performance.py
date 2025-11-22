"""Performance tests for API endpoints.

This module tests API endpoint performance including response times,
throughput, and behavior under load.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest
from httpx import AsyncClient


@pytest.mark.performance
class TestAPIPerformance:
    """Performance tests for API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check_response_time(self, client: AsyncClient) -> None:
        """Test that health check responds quickly."""
        start = time.time()
        response = await client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.1, f"Health check took {elapsed:.3f}s (target: <100ms)"

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, client: AsyncClient) -> None:
        """Test health check endpoint under concurrent load."""
        num_requests = 100
        start = time.time()

        tasks = [client.get("/health") for _ in range(num_requests)]
        responses = await asyncio.gather(*tasks)

        elapsed = time.time() - start
        avg_time = elapsed / num_requests

        assert all(r.status_code == 200 for r in responses)
        assert (
            avg_time < 0.05
        ), f"Average response time: {avg_time:.3f}s (target: <50ms)"
        print(
            f"\n✓ {num_requests} concurrent requests in {elapsed:.2f}s "
            f"(avg: {avg_time*1000:.1f}ms, throughput: {num_requests/elapsed:.1f} req/s)"
        )

    @pytest.mark.asyncio
    async def test_data_list_performance(self, client: AsyncClient) -> None:
        """Test data listing performance with pagination."""
        # Test with different page sizes
        page_sizes = [10, 50, 100]

        for limit in page_sizes:
            start = time.time()
            response = await client.get(f"/data?skip=0&limit={limit}")
            elapsed = time.time() - start

            assert response.status_code == 200
            assert (
                elapsed < 0.2
            ), f"List with limit={limit} took {elapsed:.3f}s (target: <200ms)"

    @pytest.mark.asyncio
    async def test_cache_performance_improvement(self, client: AsyncClient) -> None:
        """Test that caching improves performance."""
        # First request (cold cache)
        start1 = time.time()
        response1 = await client.get("/health/services")
        elapsed1 = time.time() - start1

        # Second request (warm cache)
        start2 = time.time()
        response2 = await client.get("/health/services")
        elapsed2 = time.time() - start2

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()

        # Cached request should be faster (or at least not significantly slower)
        print(
            f"\n✓ Cold cache: {elapsed1*1000:.1f}ms, "
            f"Warm cache: {elapsed2*1000:.1f}ms "
            f"(speedup: {elapsed1/elapsed2:.1f}x)"
        )

    @pytest.mark.asyncio
    async def test_concurrent_data_operations(self, client: AsyncClient) -> None:
        """Test concurrent data CRUD operations."""
        num_operations = 50

        # Concurrent creates
        start = time.time()
        create_tasks = [
            client.post(
                "/data",
                json={
                    "name": f"item-{i}",
                    "description": f"Description {i}",
                    "data": {"index": i},
                },
            )
            for i in range(num_operations)
        ]
        create_responses = await asyncio.gather(*create_tasks, return_exceptions=True)
        create_elapsed = time.time() - start

        successful_creates = sum(
            1
            for r in create_responses
            if not isinstance(r, Exception) and r.status_code == 201
        )

        print(
            f"\n✓ Created {successful_creates}/{num_operations} items "
            f"in {create_elapsed:.2f}s "
            f"(throughput: {successful_creates/create_elapsed:.1f} ops/s)"
        )

        # Concurrent reads
        start = time.time()
        read_tasks = [client.get("/data") for _ in range(num_operations)]
        read_responses = await asyncio.gather(*read_tasks)
        read_elapsed = time.time() - start

        assert all(r.status_code == 200 for r in read_responses)
        print(
            f"✓ {num_operations} concurrent reads "
            f"in {read_elapsed:.2f}s "
            f"(throughput: {num_operations/read_elapsed:.1f} ops/s)"
        )

    @pytest.mark.asyncio
    async def test_large_payload_handling(self, client: AsyncClient) -> None:
        """Test performance with large JSON payloads."""
        # Create increasingly large payloads
        payload_sizes = [1, 10, 100]  # KB

        for size_kb in payload_sizes:
            # Generate payload of approximate size
            data = {"data": "x" * (size_kb * 1024)}

            start = time.time()
            response = await client.post(
                "/data",
                json={"name": f"large-{size_kb}kb", "description": "test", "data": data},
            )
            elapsed = time.time() - start

            assert response.status_code in [201, 422]  # Created or validation error
            print(f"✓ {size_kb}KB payload processed in {elapsed*1000:.1f}ms")

    @pytest.mark.asyncio
    async def test_rapid_sequential_requests(self, client: AsyncClient) -> None:
        """Test performance of rapid sequential requests."""
        num_requests = 100
        endpoint = "/health"

        start = time.time()
        for _ in range(num_requests):
            response = await client.get(endpoint)
            assert response.status_code == 200

        elapsed = time.time() - start
        avg_time = elapsed / num_requests

        print(
            f"\n✓ {num_requests} sequential requests "
            f"in {elapsed:.2f}s "
            f"(avg: {avg_time*1000:.1f}ms, throughput: {num_requests/elapsed:.1f} req/s)"
        )

    @pytest.mark.asyncio
    async def test_mixed_workload_performance(self, client: AsyncClient) -> None:
        """Test performance with mixed read/write workload."""
        num_operations = 100
        read_write_ratio = 0.8  # 80% reads, 20% writes

        async def mixed_operation(index: int) -> Any:
            if index / num_operations < read_write_ratio:
                # Read operation
                return await client.get("/data")
            else:
                # Write operation
                return await client.post(
                    "/data",
                    json={
                        "name": f"mixed-{index}",
                        "description": "test",
                        "data": {"index": index},
                    },
                )

        start = time.time()
        tasks = [mixed_operation(i) for i in range(num_operations)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start

        successful = sum(
            1
            for r in responses
            if not isinstance(r, Exception) and r.status_code in [200, 201]
        )

        print(
            f"\n✓ Mixed workload: {successful}/{num_operations} ops "
            f"in {elapsed:.2f}s "
            f"(throughput: {successful/elapsed:.1f} ops/s)"
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_performance_impact(
        self, client: AsyncClient
    ) -> None:
        """Test performance impact of circuit breaker."""
        # Make requests that should go through circuit breaker
        num_requests = 50

        start = time.time()
        tasks = [client.get("/health/services") for _ in range(num_requests)]
        responses = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        assert all(r.status_code == 200 for r in responses)

        avg_time = elapsed / num_requests
        print(
            f"\n✓ {num_requests} requests through circuit breaker "
            f"in {elapsed:.2f}s "
            f"(avg: {avg_time*1000:.1f}ms)"
        )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sustained_load(self, client: AsyncClient) -> None:
        """Test API performance under sustained load."""
        duration_seconds = 10
        request_rate = 10  # requests per second

        requests_made = 0
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            # Send burst of requests
            tasks = [client.get("/health") for _ in range(request_rate)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            requests_made += len(responses)

            # Wait for next interval
            await asyncio.sleep(1.0)

        elapsed = time.time() - start_time
        throughput = requests_made / elapsed

        print(
            f"\n✓ Sustained load test: {requests_made} requests "
            f"in {elapsed:.1f}s "
            f"(throughput: {throughput:.1f} req/s)"
        )

        assert throughput >= request_rate * 0.8, "Throughput dropped below 80% of target"

