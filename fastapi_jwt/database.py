import os

import sqlmodel as sql
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from .models import Salts, Users

connectionUrl = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///auth.db")
asyncEngine = AsyncEngine(sql.create_engine(connectionUrl, echo=False))

async def initDatabase():
    async with asyncEngine.begin() as conn:
        await conn.run_sync(sql.SQLModel.metadata.create_all)
        
        
async def newSession():
    asyncSession = sessionmaker(
        asyncEngine,
        class_ = AsyncSession,
        expire_on_commit = True
    )
    async with asyncSession() as session:
        async with session.begin():
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
    query = (
        sql
        .select(Users.username)
        .filter(Users.username == username)
    )
    results = await session.exec(query)
    results = results.fetchmany()
    return len(results) > 0
