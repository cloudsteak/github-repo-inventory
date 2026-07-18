"""Tests for GitHub client rate-limit handling."""

from github_repo_inventory.github_client import GitHubClient
from httpx import Response


def _response(status_code: int, *, text: str = "{}", headers: dict[str, str] | None = None) -> Response:
    return Response(status_code=status_code, text=text, headers=headers or {}, request=None)


def test_permission_forbidden_is_not_rate_limited():
    client = GitHubClient("token")
    response = _response(
        403,
        text='{"message":"Resource not accessible by integration"}',
        headers={"X-RateLimit-Remaining": "4321"},
    )

    assert client._is_rate_limit_response(response) is False


def test_primary_rate_limit_uses_remaining_header():
    client = GitHubClient("token")
    response = _response(
        403,
        text='{"message":"API rate limit exceeded for user ID 1."}',
        headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1700000000"},
    )

    assert client._is_rate_limit_response(response) is True


def test_secondary_rate_limit_message_is_detected():
    client = GitHubClient("token")
    response = _response(
        403,
        text='{"message":"You have exceeded a secondary rate limit. Please wait a few minutes."}',
        headers={"X-RateLimit-Remaining": "100"},
    )

    assert client._is_rate_limit_response(response) is True
