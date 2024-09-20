import os
from typing import Tuple

import sqlmodel as sql
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from .hashing import currentUTCDateTime
from .models import Salts, Users

# connectionUrl = os.getenv("DATABASE_URL", "mysql+asyncmy://arnabd64:secure-password@172.17.0.2:3306/auth")
connectionUrl = "mysql+asyncmy://arnabd64:secure-password@172.17.0.2:3306/auth"
asyncEngine = AsyncEngine(sql.create_engine(connectionUrl, echo=True))


async def initDatabase():
    async with asyncEngine.begin() as conn:
        await conn.run_sync(sql.SQLModel.metadata.create_all)


async def newSession():
    asyncSession = sessionmaker(asyncEngine, class_=AsyncSession, expire_on_commit=True)
    async with asyncSession() as session:
        yield session


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
    query = sql.select(Users.username).filter(Users.username == username)
    async with session.begin():
        results = await session.exec(query)
    results = results.fetchmany()
    return len(results) > 0


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
    async with session.begin():
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
    async with session.begin():
        results = await session.exec(query)
    print(results)


async def updateDatabaseWithNewUser(
    user: Users, salt: Salts, session: AsyncSession
) -> None:
    # build the queries
    user_query = sql.insert(Users).values(**user.model_dump())
    salt_query = sql.insert(Salts).values(**salt.model_dump())

    # execute them
    async with session.begin():
        _ = await session.exec(user_query)
        _ = await session.exec(salt_query)
