from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Base class for domain models with strict input validation."""

    model_config = ConfigDict(extra="forbid")


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""

    return datetime.now(UTC)
