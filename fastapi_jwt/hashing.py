import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple, Any

import jwt
import ulid


def currentUTCDateTime() -> datetime:
    return datetime.now(timezone.utc)


def randomULID() -> bytes:
    return ulid.ULID().bytes


def tokenLifeSpan(lifespan: int = 30) -> Tuple[float, float]:
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
    issue = datetime.now(timezone.utc).timestamp()
    expiry = issue + lifespan
    return issue, expiry


def decodeTimestamp(unix_timestamp: float, *, format=r"%Y-%m-%d %M:%M:%S %Z"):
    return datetime.fromtimestamp(unix_timestamp, timezone.utc).strftime(format)


def hashPassword(
    plain_text_password: str, salt: Optional[bytes] = None
) -> Tuple[bytes, bytes]:
    # generate a random salt if salt is None
    if salt is None:
        salt = os.urandom(16)

    # convert plain text password to bytes
    if isinstance(plain_text_password, str):
        plain_text_password = plain_text_password.encode("utf-8")

    # hash the pasword
    hashed_password = hashlib.scrypt(
        password=plain_text_password, salt=salt, n=2**14, r=8, p=1, dklen=128
    )

    return hashed_password, salt


def verifyPassword(
    plain_text_password: str, hashed_password: bytes, salt: bytes
) -> bool:
    candidate_password, _ = hashPassword(plain_text_password, salt)
    return hmac.compare_digest(candidate_password, hashed_password)


def issueJSONWebToken(
    username: str, *, headers: Optional[Dict[str, str]] = None
) -> str:
    # get the timestamps for issue and expiry
    iat, exp = tokenLifeSpan(int(os.getenv("JWT_LIFESPAN")))

    # prepare the payload
    payload = {"sub": username, "iat": iat, "exp": exp}
    return jwt.encode(
        payload,
        key="727FC49123C0D17296E26FFFEDDB09799156C5943A4A9F6294FEB7A4585AA640",
        algorithm=os.getenv("JWT_ALGORITHM"),
        headers=headers,
    )


def decodeJSONWebToken(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(
            token,
            key="727FC49123C0D17296E26FFFEDDB09799156C5943A4A9F6294FEB7A4585AA640",
            algorithms=[os.getenv("JWT_ALGORITHM")],
            verify=True,
            leeway=timedelta(seconds=int(os.getenv("JWT_LIFESPAN"))),
        )
    except jwt.PyJWTError:
        return None
    return payload
