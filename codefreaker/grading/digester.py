import hashlib


class Digester:
    """Simple wrapper of hashlib using our preferred hasher."""

    def __init__(self):
        self._hasher = hashlib.sha1()

    def update(self, b):
        """Add the bytes b to the hasher."""
        self._hasher.update(b)

    def digest(self):
        """Return the digest as an hex string."""
        return self._hasher.digest().hex()
