"""Confluence-related Celery tasks.

This module contains tasks for asynchronous Confluence operations,
including comprehensive statistics collection.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import httpx

from src.worker.celery_app import celery_app
from src.worker.exceptions import WorkerError
from src.worker.services.confluence_client import ConfluenceClient

logger = logging.getLogger(__name__)


def _collect_confluence_statistics_impl(self, event_data: dict[str, Any]) -> dict[str, Any]:
    job_id = event_data.get("job_id")
    space_key = event_data.get("space_key")
    callback_url = event_data.get("callback_url")

    logger.info(f"Starting statistics collection: job_id={job_id}, space_key={space_key}")

    try:
        # Get Confluence credentials from environment (or Vault)
        confluence_base_url = os.environ.get("CONFLUENCE_BASE_URL")
        confluence_email = os.environ.get("CONFLUENCE_EMAIL")
        confluence_api_token = os.environ.get("CONFLUENCE_API_TOKEN")

        # If not in env, try to get from Vault
        if not all([confluence_base_url, confluence_email, confluence_api_token]):
            credentials = _get_credentials_from_vault()
            confluence_base_url = credentials["base_url"]
            confluence_email = credentials["email"]
            confluence_api_token = credentials["api_token"]

        # Track collection time
        start_time = time.time()

        # Collect statistics
        with ConfluenceClient(
            base_url=confluence_base_url,
            email=confluence_email,
            api_token=confluence_api_token,
        ) as client:
            statistics = client.get_comprehensive_statistics(space_key)

        collection_time = time.time() - start_time

        # Prepare callback payload
        from datetime import datetime

        callback_payload = {
            "job_id": job_id,
            "space_key": space_key,
            "status": "completed",
            "statistics": {
                "space_key": statistics["space_key"],
                "space_name": statistics.get("space_name"),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "basic": statistics["basic"],
                "detailed": statistics["detailed"],
                "comprehensive": statistics["comprehensive"],
                "collection_time_seconds": collection_time,
            },
            "error_message": None,
        }

        # Send callback to API
        _send_callback(callback_url, callback_payload)

        logger.info(
            f"Statistics collection completed: job_id={job_id}, "
            f"pages={statistics['basic']['total_pages']}, "
            f"time={collection_time:.2f}s"
        )

        return {
            "status": "success",
            "job_id": job_id,
            "space_key": space_key,
            "collection_time_seconds": collection_time,
        }

    except WorkerError as e:
        logger.error(f"Worker error in statistics collection: {e}")

        # Send failure callback
        callback_payload = {
            "job_id": job_id,
            "space_key": space_key,
            "status": "failed",
            "statistics": {},
            "error_message": str(e),
        }

        try:
            _send_callback(callback_url, callback_payload)
        except Exception as callback_error:
            logger.error(f"Failed to send error callback: {callback_error}")

        # Retry if retries remaining
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e)

        raise

    except Exception as e:
        logger.error(f"Unexpected error in statistics collection: {e}", exc_info=True)

        # Send failure callback
        callback_payload = {
            "job_id": job_id,
            "space_key": space_key,
            "status": "failed",
            "statistics": {},
            "error_message": f"Unexpected error: {str(e)}",
        }

        try:
            _send_callback(callback_url, callback_payload)
        except Exception as callback_error:
            logger.error(f"Failed to send error callback: {callback_error}")

        raise


def _get_credentials_from_vault() -> dict[str, str]:
    """Get Confluence credentials from Vault.

    Returns:
        Dictionary containing Confluence credentials

    Raises:
        WorkerError: If credentials cannot be retrieved
    """
    try:
        import hvac

        vault_addr = os.environ.get("VAULT_ADDR", "http://vault:8200")
        vault_token = os.environ.get("VAULT_TOKEN", "dev-root-token")

        client = hvac.Client(url=vault_addr, token=vault_token)

        # Read secret
        secret = client.secrets.kv.v2.read_secret_version(path="confluence/credentials")
        credentials = secret["data"]["data"]

        return {
            "base_url": credentials["base_url"],
            "email": credentials["email"],
            "api_token": credentials["api_token"],
        }

    except Exception as e:
        logger.error(f"Failed to get credentials from Vault: {e}")
        raise WorkerError(f"Failed to get Confluence credentials: {e}")


def _send_callback(callback_url: str, payload: dict[str, Any]) -> None:
    """Send callback to API with collected statistics.

    Args:
        callback_url: API callback endpoint URL
        payload: Statistics payload

    Raises:
        WorkerError: If callback fails
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(callback_url, json=payload)
            response.raise_for_status()

        logger.info(f"Callback sent successfully to {callback_url}")

    except httpx.HTTPStatusError as e:
        logger.error(f"Callback HTTP error: {e.response.status_code} - {e.response.text}")
        raise WorkerError(f"Callback failed with status {e.response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send callback: {e}")
        raise WorkerError(f"Callback failed: {e}")


@celery_app.task(name="src.worker.tasks.confluence.process_statistics_queue")
def process_statistics_queue() -> dict[str, Any]:
    """Process statistics requests from RabbitMQ queue.

    This task polls the statistics request queue and dispatches
    collection tasks for each request.

    Returns:
        Dictionary containing processing results
    """
    import pika

    try:
        # Connect to RabbitMQ
        rabbitmq_url = os.environ.get(
            "CELERY_BROKER_URL", "amqp://odin:odin_dev_password@rabbitmq:5672/"
        )

        parameters = pika.URLParameters(rabbitmq_url)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Declare queue
        queue_name = "confluence.statistics.requests"
        channel.queue_declare(queue=queue_name, durable=True)

        # Process messages
        processed = 0
        while True:
            method, properties, body = channel.basic_get(queue=queue_name, auto_ack=False)

            if method is None:
                # Queue is empty
                break

            try:
                # Parse event data
                event_data = json.loads(body.decode("utf-8"))

                # Dispatch collection task
                collect_confluence_statistics.delay(event_data)

                # Acknowledge message
                channel.basic_ack(delivery_tag=method.delivery_tag)
                processed += 1

                logger.info(f"Dispatched statistics collection for job: {event_data.get('job_id')}")

            except Exception as e:
                logger.error(f"Failed to process message: {e}")
                # Reject message (will be requeued)
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        connection.close()

        return {"status": "success", "processed": processed}

    except Exception as e:
        logger.error(f"Failed to process statistics queue: {e}")
        return {"status": "error", "error": str(e), "processed": 0}

