"""GitHub REST and GraphQL client with rate-limit awareness."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class GitHubRateLimitError(Exception):
    """Raised when GitHub rate limit is exhausted."""


class GitHubAPIError(Exception):
    """Raised for non-recoverable GitHub API failures."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubClient:
    """Minimal GitHub API client."""

    REST_BASE = "https://api.github.com"
    GRAPHQL_URL = "https://api.github.com/graphql"

    def __init__(self, token: str, max_retries: int = 3) -> None:
        self._token = token
        self._max_retries = max_retries
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._client = httpx.Client(timeout=60.0, headers=self._headers)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _handle_rate_limit(self, response: httpx.Response) -> None:
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            reset = int(response.headers.get("X-RateLimit-Reset", "0"))
            sleep_for = max(0, reset - int(time.time())) + 1
            logger.warning("Rate limit reached, sleeping for %s seconds", sleep_for)
            time.sleep(sleep_for)

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, GitHubRateLimitError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        expected_status: int | tuple[int, ...] = 200,
    ) -> httpx.Response:
        url = path if path.startswith("http") else f"{self.REST_BASE}{path}"
        response = self._client.request(method, url, params=params, json=json)

        if response.status_code == 403 and "rate limit" in response.text.lower():
            self._handle_rate_limit(response)
            raise GitHubRateLimitError("GitHub rate limit exceeded")

        if isinstance(expected_status, int):
            expected = (expected_status,)
        else:
            expected = expected_status

        if response.status_code not in expected:
            raise GitHubAPIError(
                f"GitHub API {method} {path} failed: {response.status_code} {response.text[:300]}",
                status_code=response.status_code,
            )
        return response

    def get_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        expected_status: int | tuple[int, ...] = 200,
    ) -> Any:
        response = self.request("GET", path, params=params, expected_status=expected_status)
        if response.status_code == 204:
            return None
        return response.json()

    def paginate(self, path: str, *, params: dict[str, Any] | None = None) -> list[Any]:
        """Follow GitHub REST pagination via Link headers."""
        items: list[Any] = []
        query = dict(params or {})
        query.setdefault("per_page", 100)
        url: str | None = path

        while url:
            response = self.request("GET", url, params=query if url == path else None)
            payload = response.json()
            if isinstance(payload, list):
                items.extend(payload)
            else:
                break

            next_url = None
            link_header = response.headers.get("Link", "")
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    next_url = part.split(";")[0].strip().strip("<>")
                    break
            url = next_url
            query = {}

        return items

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.request("POST", self.GRAPHQL_URL, json={"query": query, "variables": variables or {}})
        payload = response.json()
        if "errors" in payload:
            messages = "; ".join(error.get("message", str(error)) for error in payload["errors"])
            raise GitHubAPIError(f"GraphQL error: {messages}")
        return payload["data"]

    def get_authenticated_login(self) -> str:
        return self.get_json("/user")["login"]
