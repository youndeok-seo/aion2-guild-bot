from fastapi import FastAPI, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from .models.database import SessionLocal, GuildMember, CombatPowerHistory, init_db
from .services.ncsoft_client import get_ncsoft_client
from .services.chart_service import generate_combat_power_chart
from .services.equipment_image_service import generate_equipment_image


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan, title="아이온2 길드 봇 API")


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/members/register")
async def register_member(
    character_id: str,
    server_id: int,
    discord_id: str = None,
    db: Session = Depends(get_db)
):
    ncsoft = get_ncsoft_client()
    data = await ncsoft.get_character_info(character_id, server_id)

    if not data:
        raise HTTPException(404, "캐릭터를 찾을 수 없습니다")

    profile = data["profile"]

    existing = db.query(GuildMember).filter_by(character_id=character_id).first()
    if existing:
        raise HTTPException(409, "이미 등록된 캐릭터입니다")

    if discord_id:
        existing_discord = db.query(GuildMember).filter_by(discord_id=discord_id).first()
        if existing_discord:
            raise HTTPException(409, f"이미 '{existing_discord.character_name}' 캐릭터로 등록되어 있습니다")

    try:
        member = GuildMember(
            discord_id=discord_id,
            character_name=profile["characterName"],
            character_id=character_id,
            server_id=server_id,
            server_name=profile["serverName"],
            class_name=profile["className"],
            race_name=profile["raceName"],
        )
        db.add(member)
        db.flush()

        history = CombatPowerHistory(
            member_id=member.id,
            combat_power=profile["combatPower"],
            level=profile["characterLevel"],
        )
        db.add(history)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "이미 등록된 계정 또는 캐릭터입니다")

    return {"status": "ok", "character": profile["characterName"]}


@app.get("/character/{character_name}")
async def get_character(character_name: str, db: Session = Depends(get_db)):
    member = db.query(GuildMember).filter_by(character_name=character_name).first()
    if not member:
        raise HTTPException(404, f"등록되지 않은 캐릭터: {character_name}")

    ncsoft = get_ncsoft_client()
    data = await ncsoft.get_character_info(member.character_id, member.server_id)

    if not data:
        raise HTTPException(503, "NCSOFT API 호출 실패")

    profile = data["profile"]

    item_level = next(
        (s["value"] for s in data["stat"]["statList"] if s["type"] == "ItemLevel"),
        0
    )

    last = db.query(CombatPowerHistory).filter_by(member_id=member.id)\
        .order_by(CombatPowerHistory.recorded_at.desc()).first()

    if not last or last.combat_power != profile["combatPower"]:
        db.add(CombatPowerHistory(
            member_id=member.id,
            combat_power=profile["combatPower"],
            item_level=item_level,
            level=profile["characterLevel"],
        ))
        db.commit()

    return {
        "name": profile["characterName"],
        "server": profile["serverName"],
        "region": profile["regionName"],
        "class": profile["className"],
        "race": profile["raceName"],
        "gender": profile.get("genderName", ""),
        "level": profile["characterLevel"],
        "combat_power": profile["combatPower"],
        "item_level": item_level,
        "title": profile["titleName"],
        "title_grade": profile["titleGrade"],
        "profile_image": profile["profileImage"],
        "stats": [
            {
                "type": s["type"],
                "name": s["name"],
                "value": s["value"],
                "effects": s.get("statSecondList") or [],
            }
            for s in data["stat"]["statList"]
        ],
        "rankings": [
            {
                "name": r["rankingContentsName"],
                "rank": r["rank"],
                "grade": r["gradeName"],
                "point": r["point"],
                "prev_rank": r["prevRank"],
                "rank_change": r["rankChange"],
            }
            for r in data["ranking"]["rankingList"] if r["rank"] is not None
        ],
        "daevanion": [
            {
                "name": b["name"],
                "open": b["openNodeCount"],
                "total": b["totalNodeCount"],
                "percent": b["openPercent"],
            }
            for b in data.get("daevanion", {}).get("boardList", [])
        ],
    }


@app.get("/ranking")
async def get_guild_ranking(db: Session = Depends(get_db)):
    members = db.query(GuildMember).all()

    rankings = []
    for member in members:
        last = db.query(CombatPowerHistory).filter_by(member_id=member.id)\
            .order_by(CombatPowerHistory.recorded_at.desc()).first()
        if last:
            rankings.append({
                "name": member.character_name,
                "class": member.class_name,
                "combat_power": last.combat_power,
                "updated_at": last.recorded_at.isoformat(),
            })

    rankings.sort(key=lambda x: x["combat_power"], reverse=True)
    return rankings


def _build_equipment_data(data: dict) -> tuple[list, dict]:
    """NCSOFT 장비 응답에서 장비 목록(스킨 포함)과 petwing 추출"""
    equip_list = data.get("equipment", {}).get("equipmentList", [])
    skin_list  = data.get("equipment", {}).get("skinList", [])
    petwing    = data.get("petwing", {})

    # 스킨 슬롯 매핑 (귀걸이 이름 차이 보정)
    skin_by_slot: dict[str, str] = {}
    for skin in skin_list:
        slot = skin["slotPosName"]
        skin_by_slot[slot] = skin["icon"]
    if "EarringL" in skin_by_slot:
        skin_by_slot["Earring1"] = skin_by_slot["EarringL"]
    if "EarringR" in skin_by_slot:
        skin_by_slot["Earring2"] = skin_by_slot["EarringR"]

    equipment = [
        {
            "slot":      item["slotPosName"],
            "name":      item["name"],
            "grade":     item["grade"],
            "enchant":   item["enchantLevel"],
            "exceed":    item["exceedLevel"],
            "icon":      item["icon"],
            "skin_icon": skin_by_slot.get(item["slotPosName"]),
        }
        for item in equip_list
    ]
    return equipment, petwing


@app.get("/character/{character_name}/equipment")
async def get_character_equipment_info(character_name: str, db: Session = Depends(get_db)):
    member = db.query(GuildMember).filter_by(character_name=character_name).first()
    if not member:
        raise HTTPException(404, "캐릭터를 찾을 수 없습니다")

    ncsoft = get_ncsoft_client()
    data = await ncsoft.get_character_equipment(member.character_id, member.server_id)
    if not data:
        raise HTTPException(503, "NCSOFT API 호출 실패")

    equipment, petwing = _build_equipment_data(data)

    return {
        "equipment": [
            {k: v for k, v in item.items() if k != "icon" and k != "skin_icon"}
            for item in equipment
        ],
        "pet": {
            "name": petwing["pet"]["name"],
            "level": petwing["pet"]["level"],
        } if petwing.get("pet") else None,
        "wing": {
            "name": petwing["wing"]["name"],
            "grade": petwing["wing"]["grade"],
            "enchant": petwing["wing"]["enchantLevel"],
        } if petwing.get("wing") else None,
        "wing_skin": {
            "name": petwing["wingSkin"]["name"],
            "grade": petwing["wingSkin"]["grade"],
        } if petwing.get("wingSkin") else None,
    }


@app.get("/character/{character_name}/equipment/image")
async def get_equipment_image(character_name: str, db: Session = Depends(get_db)):
    member = db.query(GuildMember).filter_by(character_name=character_name).first()
    if not member:
        raise HTTPException(404, "캐릭터를 찾을 수 없습니다")

    ncsoft = get_ncsoft_client()
    data = await ncsoft.get_character_equipment(member.character_id, member.server_id)
    if not data:
        raise HTTPException(503, "NCSOFT API 호출 실패")

    equipment, _ = _build_equipment_data(data)
    img_bytes = await generate_equipment_image(equipment)
    return Response(content=img_bytes, media_type="image/png")


@app.get("/character/{character_name}/graph")
async def get_combat_power_graph(
    character_name: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    member = db.query(GuildMember).filter_by(character_name=character_name).first()
    if not member:
        raise HTTPException(404, "캐릭터를 찾을 수 없습니다")

    since = datetime.utcnow() - timedelta(days=days)
    history = db.query(CombatPowerHistory)\
        .filter(CombatPowerHistory.member_id == member.id)\
        .filter(CombatPowerHistory.recorded_at >= since)\
        .order_by(CombatPowerHistory.recorded_at).all()

    return generate_combat_power_chart(character_name, history)
