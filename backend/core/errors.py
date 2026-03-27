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


class PortraitNotFound(DomainError):
    def __init__(self, message: str = "That portrait is gone. Maybe it never survived the approval round.") -> None:
        super().__init__("PORTRAIT_NOT_FOUND", message, status.HTTP_404_NOT_FOUND)


class SwipeConflict(DomainError):
    def __init__(self, message: str = "That swipe cannot happen. Something about the target or state does not line up.") -> None:
        super().__init__("SWIPE_CONFLICT", message, status.HTTP_409_CONFLICT)


class MatchNotFound(DomainError):
    def __init__(self, message: str = "That match does not exist. Maybe they unmatched you. It happens to the best of us.") -> None:
        super().__init__("MATCH_NOT_FOUND", message, status.HTTP_404_NOT_FOUND)


class MatchConflict(DomainError):
    def __init__(self, message: str = "That match cannot do this right now. The relationship state is being difficult.") -> None:
        super().__init__("MATCH_CONFLICT", message, status.HTTP_409_CONFLICT)


class ChatConflict(DomainError):
    def __init__(self, message: str = "That chat action could not land cleanly. The conversation thread pushed back.") -> None:
        super().__init__("CHAT_CONFLICT", message, status.HTTP_409_CONFLICT)


class ChemistryConflict(DomainError):
    def __init__(self, message: str = "That chemistry test cannot start or continue from the current state.") -> None:
        super().__init__("CHEMISTRY_CONFLICT", message, status.HTTP_409_CONFLICT)


class ReviewConflict(DomainError):
    def __init__(self, message: str = "That review cannot be submitted yet. The collaboration needs a cleaner ending first.") -> None:
        super().__init__("REVIEW_CONFLICT", message, status.HTTP_409_CONFLICT)


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
