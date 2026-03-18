import fastapi, uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI

app = FastAPI()

app.mount("/", StaticFiles(directory="site", html=True))

if __name__ == "__main__":
    uvicorn.run("main:app", port=10000, reload=True)