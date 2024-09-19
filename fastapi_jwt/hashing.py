import hashlib
import hmac
import os
from typing import Optional, Tuple, Dict
import jwt
from datetime import datetime, timezone, timedelta

TOKEN_LIFESPAN = 300
SECRET = "727FC49123C0D17296E26FFFEDDB09799156C5943A4A9F6294FEB7A4585AA640"
ALGORITHM = "HS256"


def tokenLifeSpan(lifespan: int) -> Tuple[float, float]:
    """
    Generates the POSIX timestamps for the issue &
    expiry of a JSON Web Token
    
    Arguments:
    ----------
    - `lifespan`: Duration in seconds the Token is valid
    
    Returns:
    --------
    - `issue`: timestamp of token creation
    - `expiry`: timestamp of token expiration
    """
    issue = datetime.now(timezone.utc)
    expiry = issue + timedelta(seconds=lifespan)
    return issue.timestamp(), expiry.timestamp()


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
        n = 2 ** 14,
        r = 8,
        p = 1,
        dklen = 128
    )
    
    return hashed_password, salt


def verifyPassword(plain_text_password: str, hashed_password: bytes, salt: bytes) -> bool:
    candidate_password, _ = hashPassword(plain_text_password, salt)
    return hmac.compare_digest(candidate_password, hashed_password)


def issueJSONWebToken(username: str, *, headers: Optional[Dict[str, str]] = None) -> str:
    # get the timestamps for issue and expiry
    iat, exp = tokenLifeSpan(TOKEN_LIFESPAN)
    
    # prepare the payload
    payload = {
        "sub": username,
        "iat": iat,
        "exp": exp
    }
    return jwt.encode(payload, key=SECRET, algorithm=ALGORITHM, headers=headers)