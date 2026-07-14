"""Exception hierarchy for syhwp. All errors derive from :class:`SyhwpError`."""


class SyhwpError(Exception):
    """Base class for every error raised by syhwp."""


class UnsupportedFormatError(SyhwpError):
    """The file is neither an HWP 5.x (OLE) nor an HWPX (ZIP) document."""


class InvalidHwpError(SyhwpError):
    """The file looks like HWP/HWPX but is malformed or of an unsupported version."""


class EncryptedDocumentError(SyhwpError):
    """The document is password-protected or distribution (copy-protected).

    Such documents have encrypted body streams and cannot be read without the
    key, which is out of scope for syhwp.
    """
