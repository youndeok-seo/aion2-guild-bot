from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import asyncio

from .models.database import SessionLocal, GuildMember, CombatPowerHistory
from .services.ncsoft_client import get_ncsoft_client


async def daily_update_all_members():
    db = SessionLocal()
    ncsoft = get_ncsoft_client()

    members = db.query(GuildMember).all()
    print(f"[{datetime.now()}] {len(members)}명 자동 갱신 시작")

    success, failed = 0, 0
    for member in members:
        try:
            data = await ncsoft.get_character_info(member.character_id, member.server_id)
            if data:
                profile = data["profile"]
                item_level = next(
                    (s["value"] for s in data["stat"]["statList"] if s["type"] == "ItemLevel"),
                    0
                )
                db.add(CombatPowerHistory(
                    member_id=member.id,
                    combat_power=profile["combatPower"],
                    item_level=item_level,
                    level=profile["characterLevel"],
                ))
                success += 1
            await asyncio.sleep(2)
        except Exception as e:
            print(f"갱신 실패: {member.character_name} - {e}")
            failed += 1

    db.commit()
    db.close()
    print(f"[{datetime.now()}] 갱신 완료 - 성공: {success}, 실패: {failed}")


def start_scheduler():
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
    scheduler.add_job(daily_update_all_members, CronTrigger(hour=0, minute=0))
    scheduler.start()
    return scheduler
