import httpx
import asyncio
from typing import Optional
from functools import lru_cache


class NcsoftClient:
    BASE_URL = "https://aion2.plaync.com/api"

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Referer": "https://aion2.plaync.com/ko-kr/characters/index",
            },
            timeout=10.0
        )
        self._lock = asyncio.Semaphore(3)

    async def get_character_info(self, character_id: str, server_id: int) -> Optional[dict]:
        async with self._lock:
            try:
                response = await self.client.get(
                    f"{self.BASE_URL}/character/info",
                    params={
                        "lang": "ko",
                        "characterId": character_id,
                        "serverId": server_id,
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"NCSOFT API 호출 실패: {e}")
                return None

    async def get_character_equipment(self, character_id: str, server_id: int) -> Optional[dict]:
        async with self._lock:
            try:
                response = await self.client.get(
                    f"{self.BASE_URL}/character/equipment",
                    params={
                        "lang": "ko",
                        "characterId": character_id,
                        "serverId": server_id,
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError:
                return None

    async def close(self):
        await self.client.aclose()


@lru_cache()
def get_ncsoft_client() -> NcsoftClient:
    return NcsoftClient()
