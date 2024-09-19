from datetime import datetime, timezone
from typing import Annotated, Literal, Optional

import ulid
from pydantic import BaseModel
from sqlmodel import Field, SQLModel

randomULID = lambda: ulid.ULID().bytes
currentUTCTime = lambda: datetime.now(timezone.utc)


class Users(SQLModel, table=True):
    __tablename__ = "users"
    
    user_id: Annotated[Optional[bytes], Field(primary_key=True, default_factory=randomULID)]
    first_name: Annotated[str, Field(nullable=False)]
    last_name: Annotated[Optional[str], Field(None, nullable=True)]
    username: Annotated[str, Field(unique=True)]
    password: Annotated[bytes, Field()]
    
    # metadata
    active: Annotated[bool, Field(True)]
    created_on: Annotated[datetime, Field(nullable=False, default_factory=currentUTCTime)]
    last_login: Annotated[datetime, Field(nullable=False, default_factory=currentUTCTime)]
    
    
class Salts(SQLModel, table=True):
    __tablename__ = "salts"
    
    salt_id: Annotated[Optional[bytes], Field(primary_key=True, default_factory=randomULID)]
    salt: Annotated[bytes, Field(unique=True)]
    user_id: Annotated[bytes, Field(foreign_key="users.user_id")]
    
    # metadata
    created_on: Annotated[Optional[datetime], Field(nullable=False, default_factory=currentUTCTime)]
    updated_on: Annotated[Optional[datetime], Field(nullable=False, default_factory=currentUTCTime)]


class NewUserForm(BaseModel):
    
    first_name: Annotated[str, Field(...)]
    last_name: Annotated[Optional[str], Field(None)]
    username: Annotated[str, Field(min_length=8, max_length=24)]
    password: Annotated[str, Field(min_length=16, max_length=32)]
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "first_name": "Rajiv",
                    "last_name": "Sharma",
                    "username": "sharma.Rajiv.3957",
                    "password": "r@J1v_$H4rM4-(#)!"
                }
            ]
        }
    }


class AccessToken(BaseModel):
    
    access_token: str
    token_type: Literal["Bearer"]
    
    model_config = {
        "json_schema_extra" : {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
                    "token_type": "Bearer"
                }
            ]
        }
    }
