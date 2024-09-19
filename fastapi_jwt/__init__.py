import contextlib
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, status
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi_jwt import database, hashing

from .models import AccessToken, NewUserForm, Salts, Users

PREFIX = "/auth"

@ contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    await database.initDatabase()
    yield


OAuth = OAuth2PasswordBearer(tokenUrl=f"{PREFIX}/login")
SessionDependency = Annotated[AsyncSession, Depends(database.newSession)]
LoginForm = Annotated[OAuth2PasswordRequestForm, Depends()]
JSONWebToken = Annotated[str, Depends(OAuth)]
InvalidCredentials = HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid username/password")

router = APIRouter(
    prefix = PREFIX,
    lifespan = lifespan
)



@router.post("/users/new", status_code=status.HTTP_201_CREATED)
async def create_new_user(form: NewUserForm, session: SessionDependency):
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
    - __500__: Undocumented Error
    """
    # check if username exists in 
    userExistsFlag = await database.usernameExists(form.username, session)
    if userExistsFlag:
        raise HTTPException(status.HTTP_409_CONFLICT, f"username: {form.username} already exists")
    
    # hash the password
    hashed_pasword, salt = hashing.hashPassword(form.password)
    
    # create entries for Users and Salts table
    entryUsers = Users(
        first_name = form.first_name,
        last_name = form.last_name,
        username = form.username,
        password = hashed_pasword,
    )
    
    entrySalt = Salts(
        salt = salt,
        user_id = entryUsers.user_id
    )
    
    # add to database
    # TODO: move the code to database module
    try:
        session.add(entryUsers)
        session.add(entrySalt)
        await session.commit()
        
    except Exception as e:
        await session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
    
    return {"username": form.username}


@router.post("/login", response_model=AccessToken)
async def user_login(form: LoginForm, session: SessionDependency):
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
    - __500__: Undocumented Error
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
    
    # generate json web token
    token = hashing.issueJSONWebToken(user.username)
    
    # update the last login field
    # TODO: Simplify and move to database module
    try:
        await database.updateLoginTimestamp(user.username, session)
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
    
    # respond with token
    return AccessToken(access_token=token, token_type="Bearer")


@router.head("/verify/token")
async def verify_json_web_token():
    return


@router.get("/users/me")
async def current_user(token: JSONWebToken):
    pass