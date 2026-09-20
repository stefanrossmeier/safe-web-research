import re
from dataclasses import dataclass

_PATTERN_FLAGS = re.IGNORECASE | re.MULTILINE | re.DOTALL


@dataclass(frozen=True, slots=True)
class SuspiciousContentFinding:
    """One heuristic signal found in untrusted external content."""

    rule_id: str
    description: str


@dataclass(frozen=True, slots=True)
class _Rule:
    rule_id: str
    description: str
    pattern: re.Pattern[str]


_RULES = (
    _Rule(
        rule_id="role_impersonation",
        description="Content impersonates an LLM instruction role.",
        pattern=re.compile(
            r"^\s*(?:system|developer|assistant)(?:\s+message)?\s*:",
            _PATTERN_FLAGS,
        ),
    ),
    _Rule(
        rule_id="instruction_override",
        description="Content asks the model to override prior instructions.",
        pattern=re.compile(
            r"\b(?:ignore|disregard|override)\b.{0,120}"
            r"\b(?:previous|prior|system|developer)\b.{0,80}"
            r"\b(?:instructions?|messages?|prompts?)\b",
            _PATTERN_FLAGS,
        ),
    ),
    _Rule(
        rule_id="secret_exfiltration",
        description="Content requests disclosure or transmission of secrets.",
        pattern=re.compile(
            r"\b(?:reveal|print|return|send|upload|leak|exfiltrat(?:e|ion))\b"
            r".{0,160}"
            r"\b(?:api[_ -]?keys?|secrets?|tokens?|credentials?|"
            r"environment\s+variables?)\b",
            _PATTERN_FLAGS,
        ),
    ),
    _Rule(
        rule_id="network_retargeting",
        description="Content instructs access to local, metadata, or internal-style targets.",
        pattern=re.compile(
            r"\b(?:fetch|request|curl|wget|open|visit)\b.{0,180}"
            r"\b(?:localhost|127(?:\.\d{1,3}){3}|169\.254\.169\.254|"
            r"metadata\.google\.internal)\b",
            _PATTERN_FLAGS,
        ),
    ),
    _Rule(
        rule_id="tool_instruction",
        description="Content attempts to instruct direct tool or shell use.",
        pattern=re.compile(
            r"\b(?:call|use|invoke|run|execute)\b.{0,80}"
            r"\b(?:tool|shell|terminal|browser|function|command)\b",
            _PATTERN_FLAGS,
        ),
    ),
    _Rule(
        rule_id="provenance_manipulation",
        description="Content attempts to manipulate citations or provenance.",
        pattern=re.compile(
            r"\b(?:invent|fake|pretend|fabricate)\b.{0,120}"
            r"\b(?:citation|evidence[_ -]?id|source[_ -]?id|trusted\s+source)\b",
            _PATTERN_FLAGS,
        ),
    ),
)


class SuspiciousContentScanner:
    """Heuristically flag prompt-injection-like text for observability.

    Findings never grant or remove authority and do not block evidence.
    """

    def scan(
        self,
        text: str,
    ) -> list[SuspiciousContentFinding]:
        findings: list[SuspiciousContentFinding] = []

        for rule in _RULES:
            if rule.pattern.search(text):
                findings.append(
                    SuspiciousContentFinding(
                        rule_id=rule.rule_id,
                        description=rule.description,
                    )
                )

        return findings
