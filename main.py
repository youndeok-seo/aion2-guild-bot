import asyncio
import os
import discord
from discord.ext import commands
import uvicorn
from dotenv import load_dotenv

from api.main import app
from api.scheduler import start_scheduler


load_dotenv()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"✅ 봇 로그인: {bot.user}")
    await bot.load_extension("bot.cogs.character")
    await bot.load_extension("bot.cogs.ranking")
    await bot.load_extension("bot.cogs.graph")
    synced = await bot.tree.sync()
    print(f"✅ 슬래시 명령어 {len(synced)}개 동기화 완료")


async def run_api():
    port = int(os.getenv("PORT", 8000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    start_scheduler()
    print("✅ 스케줄러 시작")

    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN 환경변수가 설정되지 않았습니다")

    await asyncio.gather(
        bot.start(token),
        run_api()
    )


if __name__ == "__main__":
    asyncio.run(main())
