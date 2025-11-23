#!/usr/bin/env python3
"""Service inactivity monitoring and shutdown script.

This script monitors all API microservices for inactivity and triggers
graceful shutdown when a service has been idle beyond the configured threshold.

Run with: python scripts/check-service-inactivity.py
Or as a cron job: */1 * * * * python /path/to/check-service-inactivity.py
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import Any

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
INACTIVITY_TIMEOUT_SECONDS = int(os.environ.get("INACTIVITY_TIMEOUT_SECONDS", "300"))  # 5 minutes
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL_SECONDS", "60"))  # 1 minute
DOCKER_COMPOSE_FILE = os.environ.get("DOCKER_COMPOSE_FILE", "docker-compose.yml")
DOCKER_COMPOSE_PROJECT = os.environ.get("DOCKER_COMPOSE_PROJECT", "odin")

# Microservice definitions
MICROSERVICES = [
    {"name": "api-confluence", "port": 8001, "container": "odin-api-confluence"},
    {"name": "api-files", "port": 8002, "container": "odin-api-files"},
    {"name": "api-llm", "port": 8003, "container": "odin-api-llm"},
    {"name": "api-health", "port": 8004, "container": "odin-api-health"},
    {"name": "api-logs", "port": 8005, "container": "odin-api-logs"},
    {"name": "api-data", "port": 8006, "container": "odin-api-data"},
    {"name": "api-secrets", "port": 8007, "container": "odin-api-secrets"},
    {"name": "api-messages", "port": 8008, "container": "odin-api-messages"},
    {"name": "api-image-analysis", "port": 8009, "container": "odin-api-image-analysis"},
]


def is_container_running(container_name: str) -> bool:
    """Check if a Docker container is running.

    Args:
        container_name: Name of the container to check

    Returns:
        True if container is running, False otherwise
    """
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return container_name in result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking container status: {e}")
        return False


def get_service_metrics(service_name: str, port: int) -> dict[str, Any] | None:
    """Get activity metrics from a microservice.

    Args:
        service_name: Name of the service
        port: Port number the service is running on

    Returns:
        Activity metrics dictionary or None if service is unreachable
    """
    try:
        response = requests.get(
            f"http://localhost:{port}/internal/activity",
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.debug(f"Could not reach {service_name} on port {port}: {e}")
        return None


def stop_service(service_name: str, container_name: str) -> bool:
    """Stop a Docker Compose service gracefully.

    Args:
        service_name: Name of the service in docker-compose.yml
        container_name: Name of the Docker container

    Returns:
        True if service was stopped successfully, False otherwise
    """
    try:
        logger.info(f"Stopping service {service_name} (container: {container_name})...")
        
        # Use docker-compose stop for graceful shutdown
        result = subprocess.run(
            [
                "docker-compose",
                "-f",
                DOCKER_COMPOSE_FILE,
                "-p",
                DOCKER_COMPOSE_PROJECT,
                "stop",
                service_name,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        
        logger.info(f"Successfully stopped {service_name}")
        logger.debug(f"Output: {result.stdout}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error stopping {service_name}: {e}")
        logger.error(f"stderr: {e.stderr}")
        return False


def check_and_shutdown_inactive_services() -> None:
    """Check all services and shutdown those that are inactive.

    This function checks each microservice for inactivity and triggers
    graceful shutdown for services exceeding the inactivity threshold.
    """
    logger.info(
        f"Checking service inactivity (threshold: {INACTIVITY_TIMEOUT_SECONDS}s)..."
    )

    for service in MICROSERVICES:
        service_name = service["name"]
        container_name = service["container"]
        port = service["port"]

        # Check if container is running
        if not is_container_running(container_name):
            logger.debug(f"{service_name} is not running, skipping...")
            continue

        # Get activity metrics
        metrics = get_service_metrics(service_name, port)
        
        if metrics is None:
            logger.warning(
                f"{service_name} is running but not responding to health checks"
            )
            continue

        idle_seconds = metrics.get("idle_seconds", 0)
        request_count = metrics.get("request_count", 0)
        uptime_seconds = metrics.get("uptime_seconds", 0)

        logger.info(
            f"{service_name}: idle={idle_seconds:.0f}s, "
            f"uptime={uptime_seconds:.0f}s, requests={request_count}"
        )

        # Check if service should be shut down
        if idle_seconds >= INACTIVITY_TIMEOUT_SECONDS:
            logger.warning(
                f"{service_name} has been idle for {idle_seconds:.0f}s "
                f"(threshold: {INACTIVITY_TIMEOUT_SECONDS}s)"
            )
            
            # Perform graceful shutdown
            if stop_service(service_name, container_name):
                logger.info(f"Successfully shut down {service_name} due to inactivity")
            else:
                logger.error(f"Failed to shut down {service_name}")


def main() -> int:
    """Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        logger.info("Starting service inactivity monitor...")
        check_and_shutdown_inactive_services()
        logger.info("Service inactivity check completed")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Service inactivity monitor interrupted by user")
        return 0
        
    except Exception as e:
        logger.error(f"Unexpected error in service inactivity monitor: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

