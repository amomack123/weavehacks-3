from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "hi"}

@app.post("/")
async def post_root():
    return {"message": "hi"}