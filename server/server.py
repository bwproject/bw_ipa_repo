import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path
import uvicorn

load_dotenv()

app = FastAPI()

BASE_PATH = Path("repo")
PACKAGES = BASE_PATH / "packages"
IMAGES = BASE_PATH / "images"


@app.get("/repo/index.json")
async def get_index():
    return FileResponse(BASE_PATH / "index.json")


@app.get("/repo/packages/{file_name}")
async def get_ipa(file_name: str):
    return FileResponse(PACKAGES / file_name)


@app.get("/repo/images/{file_name}")
async def get_image(file_name: str):
    return FileResponse(IMAGES / file_name)


async def start_server():
    """
    Асинхронный запуск uvicorn внутри общего event loop
    """
    config = uvicorn.Config(
        app,
        host=os.getenv("SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("SERVER_PORT", "8000")),
        log_level="info",
        loop="asyncio",
    )

    server = uvicorn.Server(config)
    await server.serve()