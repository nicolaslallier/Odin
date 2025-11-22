#!/usr/bin/env python3
"""Service accessibility diagnostic tool.

This script checks all services through nginx and reports their status.
Use this to quickly diagnose which services are having issues.
"""

from __future__ import annotations

import sys
from typing import Dict, Any

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)


def check_service(name: str, url: str, timeout: float = 5.0) -> Dict[str, Any]:
    """Check if a service is accessible.

    Args:
        name: Service name
        url: Service URL
        timeout: Request timeout in seconds

    Returns:
        Dictionary with check results
    """
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        
        # Only consider 2xx and 3xx status codes as successful
        # 4xx and 5xx indicate service issues
        if 200 <= response.status_code < 400:
            return {
                "name": name,
                "url": url,
                "status": "✅ OK",
                "status_code": response.status_code,
                "accessible": True,
            }
        else:
            return {
                "name": name,
                "url": url,
                "status": f"❌ HTTP {response.status_code}",
                "status_code": response.status_code,
                "accessible": False,
                "error": f"Service returned HTTP {response.status_code}",
            }
    except httpx.TimeoutException:
        return {
            "name": name,
            "url": url,
            "status": "⏱️  TIMEOUT",
            "status_code": None,
            "accessible": False,
            "error": "Request timed out",
        }
    except httpx.ConnectError as e:
        return {
            "name": name,
            "url": url,
            "status": "❌ CONNECTION ERROR",
            "status_code": None,
            "accessible": False,
            "error": str(e),
        }
    except Exception as e:
        return {
            "name": name,
            "url": url,
            "status": "❌ ERROR",
            "status_code": None,
            "accessible": False,
            "error": str(e),
        }


def main() -> None:
    """Run service accessibility checks."""
    # When running inside Docker, use the nginx container name
    # When running on host, use localhost
    import os
    if os.path.exists("/.dockerenv"):
        base_url = "http://odin-nginx"
    else:
        base_url = "http://localhost"

    services = [
        ("Nginx Health", f"{base_url}/nginx-health"),
        ("Portal Root", f"{base_url}/"),
        ("Portal Health", f"{base_url}/health"),
        ("Portal Static CSS", f"{base_url}/static/css/style.css"),
        ("Ollama", f"{base_url}/ollama/"),
        ("n8n", f"{base_url}/n8n/"),
        ("RabbitMQ", f"{base_url}/rabbitmq/"),
        ("Vault UI", f"{base_url}/ui/"),
        ("MinIO", f"{base_url}/minio/"),
    ]

    print("=" * 80)
    print("Odin Service Accessibility Check")
    print("=" * 80)
    print()

    results = []
    for name, url in services:
        print(f"Checking {name}...", end=" ", flush=True)
        result = check_service(name, url)
        results.append(result)
        print(result["status"])

    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()

    # Count results
    accessible = sum(1 for r in results if r["accessible"])
    total = len(results)

    print(f"Accessible: {accessible}/{total}")
    print()

    # Show failed services
    failed = [r for r in results if not r["accessible"]]
    if failed:
        print("Failed Services:")
        print("-" * 80)
        for r in failed:
            print(f"  {r['name']}")
            print(f"    URL: {r['url']}")
            print(f"    Error: {r.get('error', 'Unknown')}")
            print()

    # Show successful services
    successful = [r for r in results if r["accessible"]]
    if successful:
        print("Successful Services:")
        print("-" * 80)
        for r in successful:
            print(f"  {r['name']}: {r['url']} (HTTP {r['status_code']})")

    print()
    print("=" * 80)

    # Exit with error code if any service failed
    if failed:
        print(f"\n⚠️  {len(failed)} service(s) failed!")
        sys.exit(1)
    else:
        print("\n✅ All services accessible!")
        sys.exit(0)


if __name__ == "__main__":
    main()

