"""Synchronous Confluence client for Celery worker.

This module provides a synchronous Confluence service for use in
Celery worker tasks that collect comprehensive statistics.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.worker.exceptions import WorkerError

logger = logging.getLogger(__name__)


class ConfluenceClient:
    """Synchronous Confluence API client for worker tasks.

    This class provides synchronous operations for collecting comprehensive
    Confluence statistics, designed for use within Celery worker tasks.

    Attributes:
        base_url: Confluence base URL
        email: User email for authentication
        api_token: Confluence API token
    """

    def __init__(self, base_url: str, email: str, api_token: str) -> None:
        """Initialize Confluence client with credentials.

        Args:
            base_url: Confluence base URL
            email: User email for authentication
            api_token: Confluence API token
        """
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self._client: httpx.Client | None = None

    def __enter__(self) -> ConfluenceClient:
        """Context manager entry.

        Returns:
            Self
        """
        self._client = httpx.Client(
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            auth=(self.email, self.api_token),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if self._client:
            self._client.close()
            self._client = None

    def _get_client(self) -> httpx.Client:
        """Get HTTP client instance.

        Returns:
            HTTP client

        Raises:
            WorkerError: If client not initialized
        """
        if self._client is None:
            raise WorkerError("Confluence client not initialized. Use context manager.")
        return self._client

    def get_comprehensive_statistics(self, space_key: str) -> dict[str, Any]:
        """Collect comprehensive statistics for a Confluence space.

        This method gathers all available statistics including basic,
        detailed, and comprehensive metrics.

        Args:
            space_key: Confluence space key

        Returns:
            Dictionary containing comprehensive statistics

        Raises:
            WorkerError: If statistics collection fails
        """
        try:
            logger.info(f"Starting comprehensive statistics collection for space: {space_key}")

            # Get space information
            space_data = self._get_space_info(space_key)

            # Get all pages with full details
            pages = self._get_all_pages(space_key)

            # Calculate basic statistics
            basic_stats = self._calculate_basic_statistics(pages)

            # Calculate detailed statistics
            detailed_stats = self._calculate_detailed_statistics(pages)

            # Calculate comprehensive statistics
            comprehensive_stats = self._calculate_comprehensive_statistics(pages)

            logger.info(
                f"Completed statistics collection for {space_key}: "
                f"{basic_stats['total_pages']} pages"
            )

            return {
                "space_key": space_data.get("key"),
                "space_name": space_data.get("name"),
                "basic": basic_stats,
                "detailed": detailed_stats,
                "comprehensive": comprehensive_stats,
            }

        except Exception as e:
            logger.error(f"Failed to collect statistics for {space_key}: {e}")
            raise WorkerError(f"Statistics collection failed: {e}")

    def _get_space_info(self, space_key: str) -> dict[str, Any]:
        """Get space information.

        Args:
            space_key: Confluence space key

        Returns:
            Space data

        Raises:
            WorkerError: If request fails
        """
        try:
            client = self._get_client()
            url = f"{self.base_url}/rest/api/space/{space_key}"

            response = client.get(url)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise WorkerError(f"Space not found: {space_key}")
            raise WorkerError(f"Failed to get space info: {e}")
        except Exception as e:
            raise WorkerError(f"Failed to get space info: {e}")

    def _get_all_pages(self, space_key: str) -> list[dict[str, Any]]:
        """Get all pages from a space with pagination.

        Args:
            space_key: Confluence space key

        Returns:
            List of page data

        Raises:
            WorkerError: If request fails
        """
        try:
            client = self._get_client()
            all_pages = []
            start = 0
            limit = 100

            while True:
                url = f"{self.base_url}/rest/api/content"
                params = {
                    "spaceKey": space_key,
                    "type": "page",
                    "expand": "body.storage,version,space,children.attachment,history,metadata.labels",
                    "limit": limit,
                    "start": start,
                }

                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                all_pages.extend(results)

                logger.debug(f"Fetched {len(results)} pages (total: {len(all_pages)})")

                # Check if there are more pages
                if "next" not in data.get("_links", {}):
                    break

                start += limit

            return all_pages

        except Exception as e:
            raise WorkerError(f"Failed to get pages: {e}")

    def _calculate_basic_statistics(self, pages: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate basic statistics from pages.

        Args:
            pages: List of page data

        Returns:
            Basic statistics dictionary
        """
        total_pages = len(pages)
        total_size = 0
        contributors = set()
        last_updated = None

        for page in pages:
            # Calculate content size
            content = page.get("body", {}).get("storage", {}).get("value", "")
            total_size += len(content.encode("utf-8"))

            # Track contributors
            version = page.get("version", {})
            contributor = version.get("by", {}).get("displayName")
            if contributor:
                contributors.add(contributor)

            # Track last updated
            updated = version.get("when")
            if updated:
                if last_updated is None or updated > last_updated:
                    last_updated = updated

        return {
            "total_pages": total_pages,
            "total_size_bytes": total_size,
            "contributor_count": len(contributors),
            "last_updated": last_updated,
        }

    def _calculate_detailed_statistics(self, pages: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate detailed statistics from pages.

        Args:
            pages: List of page data

        Returns:
            Detailed statistics dictionary
        """
        page_types = {}
        attachment_count = 0
        attachment_size = 0
        attachment_types = {}
        total_versions = 0

        for page in pages:
            # Count page types
            page_type = page.get("type", "unknown")
            page_types[page_type] = page_types.get(page_type, 0) + 1

            # Count versions
            version_number = page.get("version", {}).get("number", 1)
            total_versions += version_number

            # Count attachments
            children = page.get("children", {})
            attachments = children.get("attachment", {}).get("results", [])
            attachment_count += len(attachments)

            for attachment in attachments:
                # Track attachment types
                media_type = attachment.get("extensions", {}).get("mediaType", "unknown")
                attachment_types[media_type] = attachment_types.get(media_type, 0) + 1

                # Sum attachment sizes
                size = attachment.get("extensions", {}).get("fileSize", 0)
                attachment_size += size

        return {
            "page_breakdown_by_type": page_types,
            "attachment_stats": {
                "count": attachment_count,
                "total_size_bytes": attachment_size,
                "types": attachment_types,
            },
            "version_count": total_versions,
        }

    def _calculate_comprehensive_statistics(
        self, pages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Calculate comprehensive statistics from pages.

        Args:
            pages: List of page data

        Returns:
            Comprehensive statistics dictionary
        """
        user_activity = {}
        comment_counts = {"total": 0}
        link_analysis = {"internal": 0, "external": 0}

        for page in pages:
            # Track user activity
            creator = page.get("history", {}).get("createdBy", {}).get("displayName", "Unknown")
            if creator not in user_activity:
                user_activity[creator] = {"pages_created": 0, "total_edits": 0}

            user_activity[creator]["pages_created"] += 1

            # Track edits
            version_number = page.get("version", {}).get("number", 1)
            user_activity[creator]["total_edits"] += version_number

            # Count comments (if available in metadata)
            metadata = page.get("metadata", {})
            # Note: Comment count might not be directly available, this is a placeholder

            # Analyze links (basic implementation)
            content = page.get("body", {}).get("storage", {}).get("value", "")
            # Count Confluence internal links (ac:link)
            internal_links = content.count("ac:link")
            # Count external links (http/https)
            external_links = content.count('href="http')

            link_analysis["internal"] += internal_links
            link_analysis["external"] += external_links

        return {
            "user_activity": user_activity,
            "page_views": {},  # Placeholder - would need analytics API
            "comment_counts": comment_counts,
            "link_analysis": link_analysis,
        }

