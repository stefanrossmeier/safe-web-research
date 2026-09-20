import re

_DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)"
    r"(?:"
    r"[A-Za-z0-9]"
    r"(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"\.)*"
    r"[A-Za-z0-9]"
    r"(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"$"
)


def validate_domain(value: str) -> str:
    """Validate and normalize a plain DNS hostname.

    Schemes, ports, paths, wildcards, whitespace, and search syntax
    are deliberately rejected.
    """

    domain = value.strip().lower()

    if not domain:
        raise ValueError("domain must not be empty")

    if not _DOMAIN_PATTERN.fullmatch(domain):
        raise ValueError(f"invalid domain: {value!r}")

    return domain
