class SearchProviderError(RuntimeError):
    """Base class for search-provider failures."""


class SearchProviderConfigurationError(SearchProviderError):
    """The provider is not configured correctly."""


class SearchProviderRequestError(SearchProviderError):
    """The provider rejected the search request."""


class SearchProviderAuthenticationError(SearchProviderError):
    """Authentication with the search provider failed."""


class SearchProviderRateLimitError(SearchProviderError):
    """The provider rejected the request because of a rate limit."""

    def __init__(
        self,
        message: str,
        *,
        reset_seconds: str | None = None,
    ) -> None:
        super().__init__(message)
        self.reset_seconds = reset_seconds


class SearchProviderUnavailableError(SearchProviderError):
    """The provider could not be reached or returned a server error."""


class SearchProviderResponseError(SearchProviderError):
    """The provider returned data that violates its expected contract."""
