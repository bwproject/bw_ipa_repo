import asyncio
from bot.bot import start_bot
from server.server import start_server

async def main():
    server_task = asyncio.create_task(start_server())
    bot_task = asyncio.create_task(start_bot())
    await asyncio.gather(server_task, bot_task)

if __name__ == "__main__":
    asyncio.run(main())