from datetime import datetime
from enum import StrEnum

from pydantic import Field

from safe_web_research.domain.base import StrictModel, utc_now


class SecuritySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(StrEnum):
    URL_BLOCKED = "url_blocked"
    IP_BLOCKED = "ip_blocked"
    REDIRECT_BLOCKED = "redirect_blocked"
    RESOURCE_LIMIT = "resource_limit"
    SUSPICIOUS_CONTENT = "suspicious_content"
    PROVIDER_ERROR = "provider_error"
    POLICY_VIOLATION = "policy_violation"


MetadataValue = str | int | float | bool | None


class SecurityEvent(StrictModel):
    """Security-relevant event produced during research."""

    event_type: SecurityEventType
    severity: SecuritySeverity

    message: str = Field(min_length=1)
    source: str | None = None

    metadata: dict[str, MetadataValue] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=utc_now)
