import hashlib
import os
from typing import Optional, Tuple


def hashPassword(plain_text_password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    # generate a random salt if salt is None
    if salt is None:
        salt = os.urandom(16)
        
    # convert plain text password to bytes
    if isinstance(plain_text_password, str):
        plain_text_password = plain_text_password.encode("utf-8")
        
    # hash the pasword
    hashed_password = hashlib.scrypt(
        password = plain_text_password,
        salt = salt,
        n = 1024,
        r = 8,
        p = 1,
        dklen = 128
    )
    
    return hashed_password, salt