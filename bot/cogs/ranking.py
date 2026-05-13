import discord
from discord.ext import commands
from discord import app_commands
import httpx
import os


API_BASE = f"http://localhost:{os.getenv('PORT', '8000')}"


class RankingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.http = httpx.AsyncClient()

    @app_commands.command(name="랭킹", description="길드원 전투력 랭킹을 표시합니다")
    async def ranking(self, interaction: discord.Interaction):
        await interaction.response.defer()

        response = await self.http.get(f"{API_BASE}/ranking")
        rankings = response.json()

        if not rankings:
            await interaction.followup.send("등록된 길드원이 없습니다.")
            return

        embed = discord.Embed(
            title="🏆 길드원 전투력 랭킹",
            color=0xFFD700
        )

        medals = ['🥇', '🥈', '🥉']
        lines = []
        for i, m in enumerate(rankings[:20]):
            prefix = medals[i] if i < 3 else f"`{i+1:2d}`"
            lines.append(f"{prefix} **{m['name']}** ({m['class']}) — {m['combat_power']:,}")

        embed.description = "\n".join(lines)
        embed.set_footer(text=f"총 {len(rankings)}명")

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(RankingCog(bot))
