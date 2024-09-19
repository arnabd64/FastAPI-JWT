from fastapi import FastAPI

import fastapi_jwt

app = FastAPI()
app.include_router(fastapi_jwt.router)


@app.get("/")
async def root():
    return {"msg": "Server is Running"}
