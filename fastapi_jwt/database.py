import os
from typing import Tuple

import sqlmodel as sql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from .hashing import currentUTCDateTime
from .models import Salts, Users

connectionUrl = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///auth.db")
asyncEngine = AsyncEngine(sql.create_engine(connectionUrl, echo=False))

async def initDatabase():
    async with asyncEngine.begin() as conn:
        await conn.run_sync(sql.SQLModel.metadata.create_all)


async def newSession():
    # create a new session
    asyncSession = sessionmaker(
        asyncEngine,
        class_ = AsyncSession,
        expire_on_commit = False
    )

    session = asyncSession()
    try:
        yield session
        _ = await session.commit()

    except SQLAlchemyError as e:
        await session.rollback()
        raise e

    finally:
        _ = await session.close()


async def usernameExists(username: str, session: AsyncSession) -> bool:
    """
    Queries the database to check if an user
    with the specified username exists.

    Arguments:
    ----------
    - `username`: Specified username to query the users table

    Returns:
    --------
    - `bool`: True if username exists, else False
    """
    query = sql.select(Users).filter(Users.username == username)
    results = await session.scalar(query)
    return results is not None


async def retrieveUser(username: str, session: AsyncSession) -> Tuple[Users, Salts]:
    """
    Queries the database to retrieve the data for the User with the
    specified username

    Arguments:
    ----------
    - `username`: Specified username to query the users table

    Returns:
    --------
    - `Users`: pydantic instance containing the data from database
    """
    query = (
        sql.select(Users, Salts)
        .join(Salts, Users.user_id == Salts.user_id)
        .filter(Users.username == username)
    )
    results = await session.exec(query)
    return results.fetchone()


async def updateLoginTimestamp(username: str, session: AsyncSession) -> None:
    """
    Updates the last login time of the user
    """
    query = (
        sql.update(Users)
        .where(Users.username == username)
        .values({"last_login": currentUTCDateTime()})
    )
    _ = await session.exec(query)


async def updateDatabaseWithNewUser(user: Users, salt: Salts, session: AsyncSession) -> None:
    async with session.begin():
        session.add(user)
        session.add(salt)
        await session.commit()