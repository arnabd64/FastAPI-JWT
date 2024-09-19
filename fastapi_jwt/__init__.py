import contextlib
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, status
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi_jwt import database, hashing

from .models import NewUserForm, Salts, Users

PREFIX = "/auth"

@ contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    await database.initDatabase()
    yield


OAuth = OAuth2PasswordBearer(tokenUrl=f"{PREFIX}/login")
SessionDependency = Annotated[AsyncSession, Depends(database.newSession)]
LoginForm = Annotated[OAuth2PasswordRequestForm, Depends()]
JWT = Annotated[str, Depends(OAuth)]

router = APIRouter(
    prefix = PREFIX,
    lifespan = lifespan
)



@router.post("/users/new", status_code=status.HTTP_201_CREATED)
async def create_new_user(form: NewUserForm, session: SessionDependency):
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
    try:
        session.add(entryUsers)
        session.add(entrySalt)
        await session.commit()
        
    except Exception as e:
        await session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
    
    return {"msg": "successfully created new user", "username": form.username}


@router.post("/login")
async def user_login(form: LoginForm, session: SessionDependency):
    pass


@router.post("/users/me")
async def current_user(token: JWT):
    pass