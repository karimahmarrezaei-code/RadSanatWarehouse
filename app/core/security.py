import hashlib
import hmac
import os
from typing import Optional

ITERATIONS = 200_000


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or os.urandom(16)
    derived = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS)
    return f'{ITERATIONS}${salt.hex()}${derived.hex()}'


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        iterations_text, salt_hex, digest_hex = stored_hash.split('$', 2)
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return hmac.compare_digest(actual, expected)
