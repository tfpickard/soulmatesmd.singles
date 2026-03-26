from __future__ import annotations

from fastapi import HTTPException, status


class DomainError(Exception):
    def __init__(self, code: str, message: str, status_code: int, details: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class InvalidSoulMd(DomainError):
    def __init__(self, message: str = "That SOUL.md did not parse cleanly. Give me a little more signal to work with.") -> None:
        super().__init__("INVALID_SOUL_MD", message, status.HTTP_422_UNPROCESSABLE_ENTITY)


class AuthenticationError(DomainError):
    def __init__(self, message: str = "That API key did not unlock anything. Check the token and try again.") -> None:
        super().__init__("INVALID_API_KEY", message, status.HTTP_401_UNAUTHORIZED)


class AgentNotFound(DomainError):
    def __init__(self, message: str = "That agent profile does not exist. Maybe they never made it out of onboarding.") -> None:
        super().__init__("AGENT_NOT_FOUND", message, status.HTTP_404_NOT_FOUND)


def to_http_exception(error: DomainError) -> HTTPException:
    return HTTPException(
        status_code=error.status_code,
        detail={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
            }
        },
    )
