class FetchError(RuntimeError):
    """Base class for bounded-fetch failures."""


class FetchConfigurationError(FetchError):
    """The fetcher is configured incorrectly."""


class FetchPolicyError(FetchError):
    """A target violates the fetch security policy."""


class FetchResolutionError(FetchError):
    """DNS resolution failed or returned no usable addresses."""


class FetchConnectionError(FetchError):
    """A network connection could not be established."""


class FetchTimeoutError(FetchError):
    """A bounded network operation timed out."""


class FetchRedirectError(FetchError):
    """Redirect processing failed or violated policy."""


class FetchContentTypeError(FetchError):
    """The fetched resource has a disallowed content type."""


class FetchSizeLimitError(FetchError):
    """The fetched resource exceeded a configured size limit."""
