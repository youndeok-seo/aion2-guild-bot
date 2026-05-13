import discord
from discord.ext import commands
from discord import app_commands
import httpx
import io


API_BASE = "http://localhost:8000"


class GraphCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.http = httpx.AsyncClient()

    @app_commands.command(name="전투력추이", description="캐릭터 전투력 변화 그래프")
    @app_commands.describe(캐릭터명="조회할 캐릭터", 일수="조회 기간 (기본 30일)")
    async def graph(self, interaction: discord.Interaction, 캐릭터명: str, 일수: int = 30):
        await interaction.response.defer()

        response = await self.http.get(
            f"{API_BASE}/character/{캐릭터명}/graph",
            params={"days": 일수}
        )

        if response.status_code != 200:
            await interaction.followup.send("❌ 그래프 생성 실패 (기록된 데이터가 부족할 수 있습니다)")
            return

        file = discord.File(io.BytesIO(response.content), filename="graph.png")
        embed = discord.Embed(
            title=f"📈 {캐릭터명} 전투력 추이",
            description=f"최근 {일수}일",
            color=0x7F77DD
        )
        embed.set_image(url="attachment://graph.png")

        await interaction.followup.send(embed=embed, file=file)


async def setup(bot):
    await bot.add_cog(GraphCog(bot))
