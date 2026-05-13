import discord
from discord.ext import commands
from discord import app_commands
import httpx
import asyncio
import io
import os
import re


API_BASE = f"http://localhost:{os.getenv('PORT', '8000')}"

PRIMARY_STATS = {"STR", "DEX", "INT", "CON", "AGI", "WIS"}

GRADE_EMOJI = {
    "Legend": "🟠",
    "Epic": "🟣",
    "Unique": "🔵",
    "Special": "⚪",
}

SLOT_KO = {
    "MainHand": "주무기",
    "SubHand": "보조",
    "Helmet": "투구",
    "Shoulder": "견갑",
    "Torso": "흉갑",
    "Pants": "각반",
    "Gloves": "장갑",
    "Boots": "장화",
    "Cape": "망토",
    "Belt": "허리띠",
    "Necklace": "목걸이",
    "Earring1": "귀걸이1",
    "Earring2": "귀걸이2",
    "Ring1": "반지1",
    "Ring2": "반지2",
    "Bracelet1": "팔찌1",
    "Bracelet2": "팔찌2",
    "Rune1": "룬1",
    "Rune2": "룬2",
    "Amulet": "아뮬렛",
    "Arcana1": "아르카나1",
    "Arcana2": "아르카나2",
    "Arcana3": "아르카나3",
    "Arcana4": "아르카나4",
    "Arcana5": "아르카나5",
    "Arcana6": "아르카나6",
}

WEAPON_SLOTS  = ["MainHand", "SubHand"]
ARMOR_SLOTS   = ["Helmet", "Shoulder", "Torso", "Pants", "Gloves", "Boots", "Cape", "Belt"]
ACC_SLOTS     = ["Necklace", "Earring1", "Earring2", "Ring1", "Ring2",
                 "Bracelet1", "Bracelet2", "Rune1", "Rune2", "Amulet"]
ARCANA_SLOTS  = ["Arcana1", "Arcana2", "Arcana3", "Arcana4", "Arcana5", "Arcana6"]


def fmt_item(item: dict) -> str:
    emoji = GRADE_EMOJI.get(item["grade"], "⬜")
    slot  = SLOT_KO.get(item["slot"], item["slot"])
    enc   = f"+{item['enchant']}" if item["enchant"] else ""
    exc   = f" 초월{item['exceed']}" if item.get("exceed") else ""
    return f"`{slot}` {emoji} {item['name']} {enc}{exc}"


def build_slot_text(items_by_slot: dict, slots: list) -> str:
    lines = []
    for s in slots:
        if s in items_by_slot:
            lines.append(fmt_item(items_by_slot[s]))
    return "\n".join(lines) if lines else "정보 없음"


def rank_arrow(change):
    if change is None or change == 0:
        return "→"
    return f"▲{change}" if change > 0 else f"▼{abs(change)}"


class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.http = httpx.AsyncClient()

    @app_commands.command(name="등록", description="길드원 캐릭터를 등록합니다")
    @app_commands.describe(url="캐릭터 정보실 URL")
    async def register(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer()

        match = re.search(r'/characters/(\d+)/([^/?#]+)', url)
        if not match:
            await interaction.followup.send("❌ 올바른 캐릭터 정보실 URL이 아닙니다.")
            return

        server_id, character_id = match.group(1), match.group(2)

        try:
            response = await self.http.post(
                f"{API_BASE}/members/register",
                params={
                    "character_id": character_id,
                    "server_id": int(server_id),
                    "discord_id": str(interaction.user.id),
                }
            )

            if response.status_code == 200:
                result = response.json()
                await interaction.followup.send(f"✅ **{result['character']}** 캐릭터가 등록되었습니다!")
            else:
                detail = response.json().get('detail', '등록 실패')
                await interaction.followup.send(f"⚠️ {detail}")
        except Exception as e:
            await interaction.followup.send(f"❌ 오류: {str(e)}")

    @app_commands.command(name="조회", description="등록된 캐릭터 정보를 조회합니다")
    @app_commands.describe(캐릭터명="조회할 캐릭터 이름")
    async def lookup(self, interaction: discord.Interaction, 캐릭터명: str):
        await interaction.response.defer()

        try:
            # 캐릭터 정보 + 장비 정보 + 장비 이미지 동시 요청
            char_res, equip_res, img_res = await asyncio.gather(
                self.http.get(f"{API_BASE}/character/{캐릭터명}"),
                self.http.get(f"{API_BASE}/character/{캐릭터명}/equipment"),
                self.http.get(f"{API_BASE}/character/{캐릭터명}/equipment/image"),
            )

            if char_res.status_code != 200:
                await interaction.followup.send(f"❌ 캐릭터를 찾을 수 없습니다: {캐릭터명}")
                return

            data  = char_res.json()
            color = 0x4A90E2 if data['race'] == '천족' else 0xD0021B

            # ── 임베드 1: 캐릭터 종합 정보 ──
            embed1 = discord.Embed(
                title=f"⚔️ {data['name']}",
                description=f"**{data['server']}** · {data['region']} 진영",
                color=color
            )
            embed1.set_thumbnail(url=data['profile_image'])

            embed1.add_field(
                name="👤 기본 정보",
                value=(
                    f"종족: {data['race']} ({data['gender']})\n"
                    f"직업: {data['class']}\n"
                    f"레벨: **Lv. {data['level']}**"
                ),
                inline=True
            )
            embed1.add_field(
                name="⚡ 전투 능력",
                value=(
                    f"전투력: **{data['combat_power']:,}**\n"
                    f"아이템 레벨: **{data['item_level']:,}**\n"
                    f"칭호: {data['title']} `{data['title_grade']}`"
                ),
                inline=True
            )
            embed1.add_field(name="​", value="​", inline=False)

            primary = [s for s in data['stats'] if s['type'] in PRIMARY_STATS]
            if primary:
                embed1.add_field(
                    name="📊 기본 스탯",
                    value="\n".join(f"{s['name']}: **{s['value']}**" for s in primary),
                    inline=True
                )

            elem = [s for s in data['stats'] if s['type'] not in PRIMARY_STATS and s['type'] != "ItemLevel"]
            if elem:
                embed1.add_field(
                    name="🔮 원소 스탯",
                    value="\n".join(f"{s['name']}: **{s['value']}**" for s in elem),
                    inline=True
                )

            embed1.add_field(name="​", value="​", inline=False)

            if data['rankings']:
                ranking_lines = []
                for r in data['rankings']:
                    arrow    = rank_arrow(r.get("rank_change"))
                    point_str = f"{r['point']:,}점" if r.get('point') else ""
                    ranking_lines.append(f"**{r['name']}**: {r['rank']}위 {arrow} `{r['grade']}` {point_str}")
                embed1.add_field(name="🏆 랭킹", value="\n".join(ranking_lines), inline=False)

            if data.get('daevanion'):
                embed1.add_field(
                    name="🌟 다에바 각성판",
                    value="\n".join(
                        f"{b['name']}: **{b['open']}/{b['total']}** ({b['percent']}%)"
                        for b in data['daevanion']
                    ),
                    inline=False
                )

            embed1.set_footer(text="NCSOFT 공식 캐릭터 정보실  |  등급: 🟠전설 🟣에픽 🔵유니크 ⚪스페셜")

            # ── 메시지 1: 캐릭터 정보 ──
            await interaction.followup.send(embed=embed1)

            # ── 메시지 2: 장비 이미지 ──
            if img_res.status_code == 200:
                img_file = discord.File(
                    io.BytesIO(img_res.content),
                    filename="equipment.png"
                )
                embed2 = discord.Embed(title="🗡️ 장비", color=color)
                embed2.set_image(url="attachment://equipment.png")
                await interaction.followup.send(embed=embed2, file=img_file)
        except Exception as e:
            await interaction.followup.send(f"❌ 오류: {str(e)}")


    @app_commands.command(name="장비", description="등록된 캐릭터의 장비를 조회합니다")
    @app_commands.describe(캐릭터명="조회할 캐릭터 이름")
    async def equipment(self, interaction: discord.Interaction, 캐릭터명: str):
        await interaction.response.defer()

        try:
            response = await self.http.get(f"{API_BASE}/character/{캐릭터명}/equipment")
            if response.status_code != 200:
                await interaction.followup.send(f"❌ 캐릭터를 찾을 수 없습니다: {캐릭터명}")
                return

            data = response.json()
            items_by_slot = {item["slot"]: item for item in data["equipment"]}

            embed = discord.Embed(
                title=f"🗡️ {캐릭터명} 장비 정보",
                color=0x8B4513
            )

            embed.add_field(
                name="⚔️ 무기",
                value=build_slot_text(items_by_slot, WEAPON_SLOTS),
                inline=False
            )
            embed.add_field(
                name="🛡️ 방어구",
                value=build_slot_text(items_by_slot, ARMOR_SLOTS),
                inline=False
            )
            embed.add_field(
                name="💍 장신구",
                value=build_slot_text(items_by_slot, ACC_SLOTS),
                inline=False
            )
            embed.add_field(
                name="🃏 아르카나",
                value=build_slot_text(items_by_slot, ARCANA_SLOTS),
                inline=False
            )

            # 펫/날개
            extra = []
            if data.get("pet"):
                extra.append(f"🐾 펫: **{data['pet']['name']}** Lv.{data['pet']['level']}")
            if data.get("wing"):
                w = data["wing"]
                emoji = GRADE_EMOJI.get(w["grade"], "⬜")
                extra.append(f"🪶 날개: {emoji} {w['name']} +{w['enchant']}")
            if data.get("wing_skin"):
                ws = data["wing_skin"]
                emoji = GRADE_EMOJI.get(ws["grade"], "⬜")
                extra.append(f"✨ 날개 외형: {emoji} {ws['name']}")

            if extra:
                embed.add_field(name="🐾 펫 / 날개", value="\n".join(extra), inline=False)

            embed.set_footer(text="등급: 🟠전설 🟣에픽 🔵유니크 ⚪스페셜")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ 오류: {str(e)}")


async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
