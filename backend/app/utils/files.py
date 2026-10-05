"""File-name/upload safety helpers shared by the (future) document upload
service. Kept here now so the storage layer and tests can rely on them."""
import re
import uuid
from pathlib import PurePosixPath


def sanitize_filename(original_filename: str) -> str:
    """Strip any directory components and unsafe characters. Used only for
    display (`original_filename` column) — never to build the on-disk path."""
    name = PurePosixPath(original_filename).name
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name[:255] or "file"


def generate_stored_filename(original_filename: str) -> str:
    """Server-generated, collision-resistant name used on disk / in storage.
    Never derived predictably from user input, which prevents path
    traversal and enumeration of other users' files."""
    suffix = PurePosixPath(sanitize_filename(original_filename)).suffix.lower()
    return f"{uuid.uuid4().hex}{suffix}"


def is_extension_allowed(filename: str, allowed_extensions: list[str]) -> bool:
    suffix = PurePosixPath(filename).suffix.lower()
    return suffix in allowed_extensions


# Magic-byte signatures for the file types this app accepts. Checked against
# the *actual* uploaded bytes so a renamed file (e.g. a script saved as
# `.pdf`) can't bypass the extension check.
_MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}

_EXTENSION_TO_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def sniff_mime_type(file_bytes: bytes) -> str | None:
    """Best-effort detection of the file's real type from its leading bytes.
    Returns None if it doesn't match any known signature."""
    for mime_type, signatures in _MAGIC_SIGNATURES.items():
        if any(file_bytes.startswith(sig) for sig in signatures):
            return mime_type
    return None


def bytes_match_claimed_extension(file_bytes: bytes, filename: str) -> bool:
    """True only if the file's magic bytes match the type implied by its
    extension. Used to reject a renamed/spoofed upload even though its
    extension passed `is_extension_allowed`."""
    suffix = PurePosixPath(filename).suffix.lower()
    expected_mime = _EXTENSION_TO_MIME.get(suffix)
    if expected_mime is None:
        return False
    return sniff_mime_type(file_bytes) == expected_mime
