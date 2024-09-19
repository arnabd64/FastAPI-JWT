import contextlib
from typing import Annotated

from fastapi import APIRouter, FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

PREFIX = "/auth"

@ contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    _ = app.version
    yield


oauth = OAuth2PasswordBearer(tokenUrl=f"{PREFIX}/login")


router = APIRouter(
    prefix = PREFIX,
    lifespan = lifespan
)


@router.post("/users/new")
async def create_new_user(form, session):
    pass


@router.post("/login")
async def user_login(credentials: Annotated[OAuth2PasswordRequestForm, Depends()], session):
    pass


@router.post("/users/me")
async def current_user(token: Annotated[str, Depends(oauth)]):
    pass