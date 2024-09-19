import contextlib
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, status
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi_jwt import database, hashing

from .models import AccessToken, NewUserForm, Salts, Users

PREFIX = "/auth"


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    await database.initDatabase()
    yield


# Dependency Injections
OAuth2Flow = OAuth2PasswordBearer(tokenUrl=f"{PREFIX}/login")
DatabaseSession = Annotated[AsyncSession, Depends(database.newSession)]
OAuth2LoginForm = Annotated[OAuth2PasswordRequestForm, Depends()]
JSONWebToken = Annotated[str, Depends(OAuth2Flow)]

# Exceptions
InvalidCredentials = HTTPException(
    status.HTTP_401_UNAUTHORIZED, "invalid username/password"
)
InvalidJSONWebToken = HTTPException(
    status.HTTP_401_UNAUTHORIZED, "invalid bearer token"
)
ExpiredJSONWebToken = HTTPException(
    status.HTTP_403_FORBIDDEN, "bearer token has expired"
)
UserExists = HTTPException(status.HTTP_409_CONFLICT, "username already exists")


router = APIRouter(prefix=PREFIX, lifespan=lifespan, tags=["Authentication"])


@router.post("/users/new", status_code=status.HTTP_201_CREATED)
async def create_new_user(form: NewUserForm, session: DatabaseSession):
    """
    Description:
    ------------
    Endpoint for new user signup.

    Body Parameters:
    ------------
    - `first_name`: (_string_) First name of the User
    - `last_name` : (_string_) [**Optional**] Last name of the User
    - `username`  : (_string_) username that will be used for future logins
    - `password`  : (_string_) password to authenticate the user

    Responses:
    ----------
    - __201__: Successfully created the user
    - __409__: Existing User attempting to Sign Up
    - __422__: Invalid value passed through Body Params
    - __500__: Undocumented Internal Error
    """
    # check if username exists in
    userExistsFlag = await database.usernameExists(form.username, session)
    if userExistsFlag:
        raise UserExists

    # hash the password
    hashed_password, salt = hashing.hashPassword(form.password)

    # create entries for Users and Salts table
    entryUsers = Users(
        first_name=form.first_name,
        last_name=form.last_name,
        username=form.username,
        password=hashed_password,
    )

    entrySalt = Salts(salt=salt, user_id=entryUsers.user_id)

    await database.updateDatabaseWithNewUser(entryUsers, entrySalt, session)

    return {"username": form.username}


@router.post("/login", response_model=AccessToken)
async def user_login(form: OAuth2LoginForm, session: DatabaseSession):
    """
    Description:
    ------------
    Endpoint for User Login and for issuing a new JSON Web Token

    Form Parameters:
    ----------------
    - `username`: (_string_)
    - `password`: (_string_)

    Responses:
    ---------
    - __200__: User Authentication was Successful and Generated an Access Token
    - __401__: User Authentication Failed
    - __500__: Undocumented Internal Error
    """
    # check if the user exists
    userExistsFlag = await database.usernameExists(form.username, session)
    if not userExistsFlag:
        raise InvalidCredentials

    # retrieve the user details
    user, salt = await database.retrieveUser(form.username, session)

    # verify password
    passwordVerified = hashing.verifyPassword(form.password, user.password, salt.salt)
    if not passwordVerified:
        raise InvalidCredentials

    # verify user is active
    if not user.active:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    await database.updateLoginTimestamp(user.username, session)

    token = hashing.issueJSONWebToken(form.username)

    return AccessToken(access_token=token, token_type="Bearer")


@router.get("/users/me")
async def current_user(token: JSONWebToken):
    """
    Endpoint to verify a JSON Web Token and retrieve
    the username from the Token

    Arguments:
    ----------
    - `token`: JSON Web Token passed as a Header

    Responses:
    ----------
    - __200__: Bearer token was successfully decoded
    - __401__: Failed to decode bearer token
    - __403__: bearer token has expired
    - __500__: Undocumented Internal Error
    """
    payload = hashing.decodeJSONWebToken(token)
    if payload is None:
        raise InvalidJSONWebToken

    if payload["exp"] <= hashing.currentUTCDateTime().timestamp():
        raise ExpiredJSONWebToken

    return {
        "username": payload["sub"],
        "issued": hashing.decodeTimestamp(payload["iat"]),
        "expiry": hashing.decodeTimestamp(payload["exp"]),
    }
