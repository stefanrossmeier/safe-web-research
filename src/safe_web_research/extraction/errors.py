class ExtractionError(RuntimeError):
    """Base class for document extraction failures."""


class UnsupportedContentTypeError(ExtractionError):
    """The extractor does not support the document content type."""


class EmptyContentError(ExtractionError):
    """The document contains no usable textual content."""
