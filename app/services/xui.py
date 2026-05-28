import aiohttp
import uuid
from datetime import datetime
from app.config import settings


class XUIService:
    def __init__(self):
        self.host = settings.XUI_HOST
        self.path = settings.XUI_PATH
        self.username = settings.XUI_USERNAME
        self.password = settings.XUI_PASSWORD
        self.inbound_id = settings.XUI_INBOUND_ID
        self.session: aiohttp.ClientSession | None = None
        self.cookie = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False)
            )
        return self.session

    async def login(self) -> bool:
        session = await self._get_session()
        url = f"{self.host}{self.path}login"
        data = {"username": self.username, "password": self.password}
        async with session.post(url, data=data) as resp:
            print(f"DEBUG login status: {resp.status}")
            text = await resp.text()
            print(f"DEBUG login response: {text[:200]}")
            if resp.status == 200:
                self.cookie = resp.cookies
                return True
            return False

    async def create_client(
        self,
        email: str,
        days: int,
        traffic_gb: int = 100
    ) -> dict | None:
        await self.login()
        session = await self._get_session()

        client_uuid = str(uuid.uuid4())
        expire_ms = int(datetime.utcnow().timestamp() * 1000) + days * 86400 * 1000
        traffic_bytes = traffic_gb * 1024 ** 3

        payload = {
            "id": self.inbound_id,
            "settings": f'{{"clients": [{{"id": "{client_uuid}", "email": "{email}", "limitIp": 3, "totalGB": {traffic_bytes}, "expiryTime": {expire_ms}, "enable": true, "tgId": "", "subId": "", "flow": "xtls-rprx-vision"}}]}}'
        }

        url = f"{self.host}{self.path}panel/api/inbounds/addClient"
        async with session.post(url, json=payload, cookies=self.cookie) as resp:
            text = await resp.text()
            print(f"DEBUG addClient response: {text[:500]}")
            try:
                data = await resp.json(content_type=None)
            except Exception as e:
                print(f"DEBUG JSON error: {e}")
                text = await resp.text()
                print(f"DEBUG response text: {text[:300]}")
                return None

            if not data:
                return None

            if data.get("success"):
                return {"uuid": client_uuid, "email": email}
            return None

    async def get_client_sub_link(self, email: str) -> str | None:
        await self.login()
        session = await self._get_session()

        url = f"{self.host}{self.path}panel/api/inbounds/getClientTraffics/{email}"
        async with session.get(url, cookies=self.cookie) as resp:
            data = await resp.json()
            if data.get("success") and data.get("obj"):
                sub_id = data["obj"].get("subId", "")
                if sub_id:
                    return f"{self.host}/sub/{sub_id}"
            return None

    async def delete_client(self, client_uuid: str) -> bool:
        await self.login()
        session = await self._get_session()

        url = f"{self.host}{self.path}panel/api/inbounds/{self.inbound_id}/delClient/{client_uuid}"
        async with session.post(url, cookies=self.cookie) as resp:
            data = await resp.json()
            return data.get("success", False)

    async def update_client_expiry(self, email: str, client_uuid: str, days: int) -> bool:
        await self.login()
        session = await self._get_session()

        expire_ms = int(datetime.utcnow().timestamp() * 1000) + days * 86400 * 1000

        payload = {
            "id": self.inbound_id,
            "settings": f'{{"clients": [{{"id": "{client_uuid}", "email": "{email}", "expiryTime": {expire_ms}, "enable": true, "flow": "xtls-rprx-vision"}}]}}'
        }

        url = f"{self.host}{self.path}panel/api/inbounds/updateClient/{client_uuid}"
        async with session.post(url, json=payload, cookies=self.cookie) as resp:
            data = await resp.json()
            return data.get("success", False)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


xui_service = XUIService()