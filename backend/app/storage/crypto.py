"""AES-256-GCM field encryption and HMAC-SHA256 blind index (ARC-007, PLN-05).

Ciphertext format: ``nonce (12 bytes) || ciphertext || GCM tag (16 bytes)``.
A fresh random 96-bit nonce is used for every value. Optional *associated
data* binds a ciphertext to its row (e.g. the patient ID): a blob copied into
another patient's row fails authentication instead of showing another
patient's data.

Blind index: ``HMAC-SHA256(INDEX_KEY, normalize_name(name))`` allows an exact
name search without decrypting any row (ADR-001, closes RSK-06).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import unicodedata
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_BYTES = 32  # AES-256
NONCE_BYTES = 12  # 96-bit nonce recommended for GCM
TAG_BYTES = 16


class DecryptionError(Exception):
    """Ciphertext was modified, belongs to another row, or the key is wrong."""


# Implements REQ-010, REQ-020
# Controls RISK-007
class FieldCipher:
    """Encrypts and decrypts single database fields with AES-256-GCM.

    REQ-020 (overhead <= 20 ms p95): one small authenticated encryption per
    field via OpenSSL (``cryptography``), no key derivation per call; the
    measured p95 is reported by TC-020.
    """

    def __init__(self, key: bytes) -> None:
        if len(key) != KEY_BYTES:
            raise ValueError(f"AES-256-GCM needs a {KEY_BYTES}-byte key, got {len(key)}")
        self._aesgcm = AESGCM(key)

    def encrypt(self, plaintext: bytes, associated_data: bytes | None = None) -> bytes:
        """Return ``nonce || ciphertext || tag`` for ``plaintext``."""
        nonce = os.urandom(NONCE_BYTES)
        return nonce + self._aesgcm.encrypt(nonce, plaintext, associated_data)

    def decrypt(self, blob: bytes, associated_data: bytes | None = None) -> bytes:
        """Return the plaintext; raise :class:`DecryptionError` if authentication fails."""
        if len(blob) < NONCE_BYTES + TAG_BYTES:
            raise DecryptionError("ciphertext is too short")
        nonce, ciphertext = blob[:NONCE_BYTES], blob[NONCE_BYTES:]
        try:
            return self._aesgcm.decrypt(nonce, ciphertext, associated_data)
        except InvalidTag as exc:
            raise DecryptionError("authentication failed (tampered data or wrong key)") from exc

    def encrypt_text(self, text: str, associated_data: bytes | None = None) -> bytes:
        """Encrypt a UTF-8 string."""
        return self.encrypt(text.encode("utf-8"), associated_data)

    def decrypt_text(self, blob: bytes, associated_data: bytes | None = None) -> str:
        """Decrypt a value written by :meth:`encrypt_text`."""
        return self.decrypt(blob, associated_data).decode("utf-8")

    def encrypt_json(self, value: Any, associated_data: bytes | None = None) -> bytes:
        """Encrypt a JSON-serialisable value (used for the vital-sign blob)."""
        payload = json.dumps(value, separators=(",", ":"), sort_keys=True)
        return self.encrypt(payload.encode("utf-8"), associated_data)

    def decrypt_json(self, blob: bytes, associated_data: bytes | None = None) -> Any:
        """Decrypt a value written by :meth:`encrypt_json`."""
        return json.loads(self.decrypt(blob, associated_data))


def normalize_name(name: str) -> str:
    """Canonical form of a name for the blind index.

    Unicode NFC, surrounding whitespace removed, inner whitespace collapsed to
    one space, case-folded. Turkish dotted/dotless I is folded explicitly
    because ``str.casefold`` is not locale aware: ``"YILMAZ".casefold()`` is
    ``"yilmaz"`` but ``"Yılmaz".casefold()`` is ``"yılmaz"``, and ``"İ"``
    becomes ``"i"`` + combining dot. After folding, ``I``, ``ı``, ``İ`` and
    ``i`` all become ``i``, so ``"AYŞE YILMAZ"`` and ``"Ayşe Yılmaz"`` match.
    Only these differences are tolerated: the index supports exact matches,
    not partial or fuzzy search (ADR-001).
    """
    folded = " ".join(unicodedata.normalize("NFC", name).split()).casefold()
    folded = folded.replace("i̇", "i").replace("ı", "i")
    return unicodedata.normalize("NFC", folded)


# Implements REQ-010
def blind_index(index_key: bytes, name: str) -> str:
    """Return the hex HMAC-SHA256 of the normalised ``name`` (64 characters)."""
    if len(index_key) < KEY_BYTES:
        raise ValueError(f"INDEX_KEY must be at least {KEY_BYTES} bytes")
    digest = hmac.new(index_key, normalize_name(name).encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()
