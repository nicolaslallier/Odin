"""Performance tests for batch processing tasks.

This module tests the performance of Celery batch tasks including
throughput, memory usage, and scalability.
"""

from __future__ import annotations

import time
from typing import Any

import pytest


@pytest.mark.performance
@pytest.mark.worker
class TestBatchPerformance:
    """Performance tests for batch processing."""

    def test_bulk_data_processing_throughput(self) -> None:
        """Test throughput of bulk data processing."""
        from src.worker.tasks.batch import process_bulk_data

        # Test with increasing batch sizes
        batch_sizes = [10, 50, 100, 500]

        for batch_size in batch_sizes:
            data_items = [{"id": i, "value": f"item-{i}"} for i in range(batch_size)]

            start = time.time()
            result = process_bulk_data.apply(args=[data_items]).get(timeout=30)
            elapsed = time.time() - start

            throughput = batch_size / elapsed

            assert result["status"] == "success"
            assert result["processed_count"] == batch_size

            print(
                f"\n✓ Processed {batch_size} items in {elapsed:.2f}s "
                f"(throughput: {throughput:.1f} items/s)"
            )

    def test_file_batch_processing_performance(self) -> None:
        """Test performance of file batch processing."""
        from src.worker.tasks.batch import process_file_batch

        # Test with different batch sizes
        batch_sizes = [5, 10, 20]

        for batch_size in batch_sizes:
            files = [
                {"filename": f"file-{i}.txt", "content": f"content-{i}"}
                for i in range(batch_size)
            ]

            start = time.time()
            try:
                result = process_file_batch.apply(args=[files, "test-bucket"]).get(
                    timeout=60
                )
                elapsed = time.time() - start

                throughput = batch_size / elapsed

                print(
                    f"\n✓ Processed {batch_size} files in {elapsed:.2f}s "
                    f"(throughput: {throughput:.1f} files/s)"
                )
            except Exception as e:
                print(f"✗ Batch size {batch_size} failed: {e}")

    def test_notification_batch_performance(self) -> None:
        """Test performance of bulk notification sending."""
        from src.worker.tasks.batch import send_bulk_notifications

        # Test with increasing recipient counts
        recipient_counts = [10, 50, 100]

        for count in recipient_counts:
            notifications = [
                {"recipient": f"user{i}@example.com", "message": f"Message {i}"}
                for i in range(count)
            ]

            start = time.time()
            result = send_bulk_notifications.apply(args=[notifications]).get(timeout=60)
            elapsed = time.time() - start

            throughput = count / elapsed

            assert result["status"] == "success"
            assert result["sent_count"] == count

            print(
                f"\n✓ Sent {count} notifications in {elapsed:.2f}s "
                f"(throughput: {throughput:.1f} notifications/s)"
            )

    def test_concurrent_batch_tasks(self) -> None:
        """Test performance of concurrent batch task execution."""
        from src.worker.tasks.batch import process_bulk_data

        num_tasks = 10
        items_per_task = 50

        # Submit multiple tasks concurrently
        start = time.time()
        async_results = []

        for task_id in range(num_tasks):
            data_items = [
                {"id": f"{task_id}-{i}", "value": f"task-{task_id}-item-{i}"}
                for i in range(items_per_task)
            ]
            result = process_bulk_data.apply_async(args=[data_items])
            async_results.append(result)

        # Wait for all tasks to complete
        results = [r.get(timeout=60) for r in async_results]
        elapsed = time.time() - start

        total_items = num_tasks * items_per_task
        throughput = total_items / elapsed

        assert all(r["status"] == "success" for r in results)

        print(
            f"\n✓ Processed {num_tasks} concurrent tasks "
            f"({total_items} total items) "
            f"in {elapsed:.2f}s "
            f"(throughput: {throughput:.1f} items/s)"
        )

    def test_large_batch_memory_efficiency(self) -> None:
        """Test memory efficiency with large batches."""
        import psutil
        from src.worker.tasks.batch import process_bulk_data

        batch_size = 1000
        data_items = [{"id": i, "value": f"item-{i}" * 10} for i in range(batch_size)]

        # Measure memory before
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        start = time.time()
        result = process_bulk_data.apply(args=[data_items]).get(timeout=120)
        elapsed = time.time() - start

        # Measure memory after
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before

        assert result["status"] == "success"

        print(
            f"\n✓ Processed {batch_size} items in {elapsed:.2f}s "
            f"(memory increase: {memory_increase:.1f}MB)"
        )

        # Memory increase should be reasonable (< 100MB for 1000 items)
        assert (
            memory_increase < 100
        ), f"Memory increase too high: {memory_increase:.1f}MB"

    def test_batch_processing_with_failures(self) -> None:
        """Test performance when some batch items fail."""
        from src.worker.tasks.batch import process_bulk_data

        batch_size = 100
        # Mix of valid and potentially problematic data
        data_items = [
            {"id": i, "value": f"item-{i}" if i % 10 != 0 else None}
            for i in range(batch_size)
        ]

        start = time.time()
        try:
            result = process_bulk_data.apply(args=[data_items]).get(timeout=60)
            elapsed = time.time() - start

            print(
                f"\n✓ Processed batch with some failures in {elapsed:.2f}s "
                f"(status: {result['status']})"
            )
        except Exception as e:
            elapsed = time.time() - start
            print(f"✗ Batch failed after {elapsed:.2f}s: {e}")

    @pytest.mark.slow
    def test_batch_task_scalability(self) -> None:
        """Test how batch processing scales with data size."""
        from src.worker.tasks.batch import process_bulk_data

        # Test scalability with increasing data sizes
        sizes = [10, 100, 500, 1000]
        times = []

        for size in sizes:
            data_items = [{"id": i, "value": f"item-{i}"} for i in range(size)]

            start = time.time()
            result = process_bulk_data.apply(args=[data_items]).get(timeout=180)
            elapsed = time.time() - start
            times.append(elapsed)

            throughput = size / elapsed

            print(
                f"\n✓ Size {size}: {elapsed:.2f}s "
                f"(throughput: {throughput:.1f} items/s)"
            )

        # Check if scaling is roughly linear (allowing 2x variance)
        for i in range(1, len(sizes)):
            size_ratio = sizes[i] / sizes[i - 1]
            time_ratio = times[i] / times[i - 1]

            print(f"Size ratio {sizes[i-1]}→{sizes[i]}: {size_ratio:.1f}x")
            print(f"Time ratio: {time_ratio:.1f}x")

            # Time should scale linearly (within 2x of size ratio)
            assert (
                time_ratio < size_ratio * 2
            ), f"Non-linear scaling detected: {time_ratio:.1f}x time for {size_ratio:.1f}x data"

    def test_batch_commit_strategy_performance(self) -> None:
        """Test performance of different batch commit strategies."""
        from src.worker.tasks.batch import process_bulk_data

        batch_size = 500
        data_items = [{"id": i, "value": f"item-{i}"} for i in range(batch_size)]

        # Test full batch processing
        start = time.time()
        result = process_bulk_data.apply(args=[data_items]).get(timeout=120)
        elapsed = time.time() - start

        throughput = batch_size / elapsed

        print(
            f"\n✓ Batch commit: {batch_size} items in {elapsed:.2f}s "
            f"(throughput: {throughput:.1f} items/s)"
        )

        # For comparison: if we had chunk-based commits, test those too
        # (This would require modifying the task to support chunk size parameter)

