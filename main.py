import asyncio
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path
from bot.bot import start_bot

load_dotenv()

BASE_PATH = Path("repo")
PACKAGES = BASE_PATH / "packages"
IMAGES = BASE_PATH / "images"
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

app = FastAPI()

@app.get("/repo/packages/{file_name}")
async def get_package(file_name: str):
    path = PACKAGES / file_name
    if path.exists():
        return FileResponse(path)
    return {"error": "File not found"}

@app.get("/repo/images/{file_name}")
async def get_image(file_name: str):
    path = IMAGES / file_name
    if path.exists():
        return FileResponse(path)
    return {"error": "File not found"}

@app.get("/repo/index.json")
async def get_index():
    path = BASE_PATH / "index.json"
    if path.exists():
        return FileResponse(path)
    return {"error": "index.json не найден"}

async def main():
    import uvicorn
    server = uvicorn.Server(
        uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    )
    await asyncio.gather(
        server.serve(),
        start_bot()
    )

if __name__ == "__main__":
    asyncio.run(main())