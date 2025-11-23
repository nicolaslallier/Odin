"""Confluence API service client.

This module provides Confluence operations including page retrieval, conversion,
backup, and statistics for the API service.
"""

from __future__ import annotations

from typing import Any

import httpx
import markdown
from markdownify import markdownify as md

from src.api.exceptions import (
    ConfluenceError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)


class ConfluenceService:
    """Confluence API service client.

    This class provides operations for interacting with Confluence Cloud API,
    including page retrieval, content conversion, space backup, and statistics.

    Attributes:
        base_url: Confluence base URL (e.g., https://your-domain.atlassian.net/wiki)
        email: User email for authentication
        api_token: Confluence API token
    """

    def __init__(self, base_url: str, email: str, api_token: str) -> None:
        """Initialize Confluence service with credentials.

        Args:
            base_url: Confluence base URL
            email: User email for authentication
            api_token: Confluence API token
        """
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self._client: httpx.AsyncClient | None = None

    async def initialize(self) -> None:
        """Initialize the HTTP client for connection pooling.

        This method creates a persistent HTTP client that will be reused
        for all requests, improving performance and resource usage.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                auth=(self.email, self.api_token),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get the HTTP client instance.

        Returns:
            HTTP client instance

        Raises:
            ServiceUnavailableError: If client not initialized
        """
        if self._client is None:
            raise ServiceUnavailableError(
                "Confluence service not initialized. Call initialize() first."
            )
        return self._client

    async def get_page_by_id(self, page_id: str) -> dict[str, Any]:
        """Retrieve a Confluence page by its ID.

        Args:
            page_id: The Confluence page ID

        Returns:
            Dictionary containing page data including title, body, space, and version

        Raises:
            ResourceNotFoundError: If page not found
            ConfluenceError: If API request fails
            ServiceUnavailableError: If Confluence service is unreachable
        """
        try:
            client = self._get_client()
            url = f"{self.base_url}/rest/api/content/{page_id}"
            params = {"expand": "body.storage,version,space"}

            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ResourceNotFoundError(f"Page not found: {page_id}", {"page_id": page_id})
            raise ConfluenceError(
                f"Failed to retrieve page: {e}",
                {"status_code": e.response.status_code, "page_id": page_id},
            )
        except httpx.RequestError as e:
            raise ServiceUnavailableError(f"Confluence service unreachable: {e}")

    async def convert_page_to_markdown(self, page_id: str) -> str:
        """Convert a Confluence page to Markdown format.

        Args:
            page_id: The Confluence page ID

        Returns:
            Page content in Markdown format

        Raises:
            ResourceNotFoundError: If page not found
            ConfluenceError: If conversion fails
            ServiceUnavailableError: If Confluence service is unreachable
        """
        page_data = await self.get_page_by_id(page_id)

        # Extract HTML content from storage format
        html_content = page_data.get("body", {}).get("storage", {}).get("value", "")

        if not html_content:
            return ""

        # Convert HTML to Markdown
        markdown_content = md(html_content, heading_style="ATX")

        return markdown_content

    def convert_markdown_to_storage(self, markdown_text: str) -> str:
        """Convert Markdown to Confluence storage format (HTML).

        Args:
            markdown_text: Markdown text to convert

        Returns:
            HTML content in Confluence storage format
        """
        if not markdown_text:
            return ""

        # Convert Markdown to HTML
        html_content = markdown.markdown(
            markdown_text,
            extensions=["extra", "codehilite", "tables", "fenced_code"],
        )

        return html_content

    async def create_or_update_page(
        self,
        space_key: str,
        title: str,
        content_html: str,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new page or update existing page in Confluence.

        Args:
            space_key: Confluence space key
            title: Page title
            content_html: Page content in HTML format (storage format)
            parent_id: Optional parent page ID

        Returns:
            Dictionary containing created/updated page data

        Raises:
            ConfluenceError: If page creation/update fails
            ServiceUnavailableError: If Confluence service is unreachable
        """
        try:
            client = self._get_client()

            # Check if page exists
            existing_page = await self._find_page_by_title(space_key, title)

            if existing_page:
                # Update existing page
                page_id = existing_page["id"]
                current_version = existing_page["version"]["number"]

                url = f"{self.base_url}/rest/api/content/{page_id}"
                payload = {
                    "version": {"number": current_version + 1},
                    "title": title,
                    "type": "page",
                    "body": {
                        "storage": {
                            "value": content_html,
                            "representation": "storage",
                        }
                    },
                }

                response = await client.put(url, json=payload)
                response.raise_for_status()
                return response.json()
            else:
                # Create new page
                url = f"{self.base_url}/rest/api/content"
                payload = {
                    "type": "page",
                    "title": title,
                    "space": {"key": space_key},
                    "body": {
                        "storage": {
                            "value": content_html,
                            "representation": "storage",
                        }
                    },
                }

                # Add parent if specified
                if parent_id:
                    payload["ancestors"] = [{"id": parent_id}]

                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            raise ConfluenceError(
                f"Failed to create/update page: {e}",
                {"status_code": e.response.status_code, "title": title},
            )
        except httpx.RequestError as e:
            raise ServiceUnavailableError(f"Confluence service unreachable: {e}")

    async def _find_page_by_title(self, space_key: str, title: str) -> dict[str, Any] | None:
        """Find a page by title in a space.

        Args:
            space_key: Confluence space key
            title: Page title to search for

        Returns:
            Page data if found, None otherwise
        """
        try:
            client = self._get_client()
            url = f"{self.base_url}/rest/api/content"
            params = {
                "spaceKey": space_key,
                "title": title,
                "expand": "version",
            }

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            return results[0] if results else None
        except (httpx.HTTPStatusError, httpx.RequestError):
            return None

    async def backup_space(self, space_key: str) -> list[dict[str, Any]]:
        """Backup all pages from a Confluence space.

        Args:
            space_key: Confluence space key

        Returns:
            List of page dictionaries containing all page data

        Raises:
            ConfluenceError: If backup fails
            ServiceUnavailableError: If Confluence service is unreachable
        """
        try:
            client = self._get_client()
            all_pages = []
            start = 0
            limit = 100  # Pages per request

            while True:
                url = f"{self.base_url}/rest/api/content"
                params = {
                    "spaceKey": space_key,
                    "type": "page",
                    "expand": "body.storage,version,space",
                    "limit": limit,
                    "start": start,
                }

                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                all_pages.extend(results)

                # Check if there are more pages
                if "next" not in data.get("_links", {}):
                    break

                start += limit

            return all_pages

        except httpx.HTTPStatusError as e:
            raise ConfluenceError(
                f"Failed to backup space: {e}",
                {"status_code": e.response.status_code, "space_key": space_key},
            )
        except httpx.RequestError as e:
            raise ServiceUnavailableError(f"Confluence service unreachable: {e}")

    async def get_space_statistics(self, space_key: str) -> dict[str, Any]:
        """Get statistics for a Confluence space.

        Args:
            space_key: Confluence space key

        Returns:
            Dictionary containing space statistics including:
            - total_pages: Number of pages in space
            - total_size_bytes: Total size of all content
            - contributors: List of unique contributors
            - last_updated: Timestamp of most recent update

        Raises:
            ConfluenceError: If statistics retrieval fails
            ServiceUnavailableError: If Confluence service is unreachable
        """
        try:
            client = self._get_client()

            # Get space info
            space_url = f"{self.base_url}/rest/api/space/{space_key}"
            space_response = await client.get(space_url)
            space_response.raise_for_status()
            space_data = space_response.json()

            # Get all pages to calculate statistics
            pages = await self.backup_space(space_key)

            # Calculate statistics
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
                "space_key": space_data.get("key"),
                "space_name": space_data.get("name"),
                "total_pages": total_pages,
                "total_size_bytes": total_size,
                "contributors": list(contributors),
                "last_updated": last_updated,
            }

        except httpx.HTTPStatusError as e:
            raise ConfluenceError(
                f"Failed to get space statistics: {e}",
                {"status_code": e.response.status_code, "space_key": space_key},
            )
        except httpx.RequestError as e:
            raise ServiceUnavailableError(f"Confluence service unreachable: {e}")

    async def health_check(self) -> bool:
        """Check if Confluence connection is healthy.

        Returns:
            True if Confluence is accessible, False otherwise
        """
        try:
            if self._client is None:
                return False

            client = self._get_client()
            response = await client.get(
                f"{self.base_url}/rest/api/space",
                timeout=httpx.Timeout(5.0),
            )
            return response.status_code == 200
        except Exception:
            return False
