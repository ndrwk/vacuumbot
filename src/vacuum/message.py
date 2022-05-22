import calendar
import datetime
import hashlib
import json
from typing import Any

from construct import (
    Adapter,
    Bytes,
    Checksum,
    Const,
    Default,
    GreedyBytes,
    Hex,
    Int16ub,
    Int32ub,
    Pointer,
    RawCopy,
    Rebuild,
    Struct,
)
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class TimeAdapter(Adapter):
    """Timestamp adapter."""

    def _encode(self, obj, context, path) -> int:
        return calendar.timegm(obj.timetuple())

    def _decode(self, obj, context, path) -> datetime.datetime:
        return datetime.datetime.utcfromtimestamp(obj)


class EncryptionAdapter(Adapter):
    """Encryption adapter."""

    @staticmethod
    def checksum(ctx: dict[str, Any]) -> bytearray:
        """Calculate a checksum.

        Args:
            ctx: context

        Returns:
            checksum as bytearray
        """
        res = bytearray(ctx['header'].data)
        res += ctx['_']['token']
        if 'data' in ctx:
            res += ctx['data'].data
        return res

    @staticmethod
    def md5(data: bytes) -> bytes:
        """Calculate a md5 hash.

        Args:
            data: data to calculate md5

        Returns:
            result as bytes
        """
        res = hashlib.md5(usedforsecurity=False)
        res.update(data)
        return res.digest()

    def key_iv(self, token: bytes) -> tuple[bytes, bytes]:
        """Generate a key and IV based on given token.

        Args:
            token: given token

        Returns:
            key and IV
        """
        key = self.md5(token)
        iv = self.md5(key + token)
        return key, iv

    def _encode(self, obj, context, path) -> bytes:
        key, iv = self.key_iv(context['_']['token'])
        padder = padding.PKCS7(128).padder()
        padded_plaintext = padder.update(
            json.dumps(obj).encode('utf-8') + b'\x00',
        )
        padded_plaintext += padder.finalize()
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        return encryptor.update(padded_plaintext) + encryptor.finalize()

    def _decode(self, obj, context, path) -> dict[str, Any]:
        key, iv = self.key_iv(context['_']['token'])
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(obj) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        unpadded_plaintext = unpadder.update(padded_plaintext)
        unpadded_plaintext += unpadder.finalize()
        return json.loads(unpadded_plaintext.rstrip(b'\x00').decode('utf-8'))


Message = Struct(
    'data' / Pointer(32, RawCopy(EncryptionAdapter(GreedyBytes))),
    'header' / RawCopy(
        Struct(
            Const(0x2131, Int16ub),
            'length' / Rebuild(Int16ub, lambda x: x._.data.length + 32),
            'unknown' / Default(Int32ub, 0x00000000),
            'device_id' / Hex(Bytes(4)),
            'ts' / TimeAdapter(Default(Int32ub, datetime.datetime.utcnow())),
        ),
    ),
    'checksum' / Checksum(
        Bytes(16),
        EncryptionAdapter.md5,
        EncryptionAdapter.checksum,
    ),
)
