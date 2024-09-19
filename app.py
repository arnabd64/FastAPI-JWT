from fastapi import FastAPI

app = FastAPI(
    title = "JWT Authentication Implementation on FastAPI"
)

@app.get("/")
async def root():
    return {"msg": "Server is Running"}