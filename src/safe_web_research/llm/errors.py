class LLMProviderError(RuntimeError):
    """Base class for language-model provider failures."""


class LLMProviderConfigurationError(LLMProviderError):
    """The provider is configured incorrectly."""


class LLMProviderAuthenticationError(LLMProviderError):
    """Authentication with the provider failed."""


class LLMProviderRequestError(LLMProviderError):
    """The provider rejected the request."""


class LLMProviderRateLimitError(LLMProviderError):
    """The provider rejected the request because of a rate limit."""


class LLMProviderUnavailableError(LLMProviderError):
    """The provider could not be reached or returned a server error."""


class LLMProviderResponseError(LLMProviderError):
    """The provider returned malformed or unusable data."""


class LLMStructuredOutputError(LLMProviderResponseError):
    """Structured output was invalid JSON or violated the requested schema."""
