import contextlib
from typing import Annotated, Any, Dict
import os

from fastapi import APIRouter, Depends, FastAPI, status
from fastapi.responses import PlainTextResponse
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi_jwt import database, hashing

from .models import AccessToken, NewUserForm, Salts, Users

PREFIX = os.getenv("AUTH_ROUTER_PREFIX", "/auth")
TOKEN_ENDPOINT = os.getenv("TOKEN_ENDPOINT", "/token")

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    await database.initDatabase()
    yield


# Dependency Injections
OAuth2Flow = OAuth2PasswordBearer(tokenUrl=f"{PREFIX}{TOKEN_ENDPOINT}")
DatabaseSession = Annotated[AsyncSession, Depends(database.newSession)]
OAuth2LoginForm = Annotated[OAuth2PasswordRequestForm, Depends()]
JSONWebToken = Annotated[str, Depends(OAuth2Flow)]

# Exceptions
InvalidCredentials = HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
InvalidToken = HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid bearer token")
ExpiredToken = HTTPException(status.HTTP_403_FORBIDDEN, "bearer token expired")
UserExists = HTTPException(status.HTTP_409_CONFLICT, "username exists")
InactiveUser = HTTPException(status.HTTP_403_FORBIDDEN, "user inactive")


router = APIRouter(prefix=PREFIX, lifespan=lifespan, tags=["Authentication"])


@router.post("/create-user", status_code=status.HTTP_201_CREATED, response_class=PlainTextResponse)
async def create_new_user(form: NewUserForm, session: DatabaseSession) -> str:
    """
    Description:
    ------------
    Endpoint for new user signup.

    Body Parameters:
    ----------------
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

    return form.username


@router.post(TOKEN_ENDPOINT, response_model=AccessToken)
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
        raise InactiveUser

    await database.updateLoginTimestamp(user.username, session)

    token = hashing.issueJSONWebToken(form.username)

    return AccessToken(access_token=token, token_type="Bearer")


@router.get("/who-am-i", response_class=PlainTextResponse)
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
        raise InvalidToken

    if payload["exp"] <= hashing.currentUTCDateTime().timestamp():
        raise ExpiredToken

    return PlainTextResponse(
        payload['sub'],
        headers = {"X-Token-Expiry": hashing.decodeTimestamp(payload["exp"])}
    )


@router.get("/extend-token", response_model=AccessToken)
async def renew_json_web_token(token: JSONWebToken):
    """
    Endpoint to reissue a valid JSON Web Token

    Arguments:
    ----------
    - `token`: JSON Web Token passes a Header

    Response:
    ---------
    - __200__: Bearer token was renewed
    """
    # get the payload
    payload = await current_user(token)

    # generate a new token
    token = hashing.issueJSONWebToken(payload['sub'])

    return AccessToken(access_token=token, token_type="Bearer")
