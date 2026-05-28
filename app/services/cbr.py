import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

_cache_rate: float | None = None
_cache_time: datetime | None = None
_CACHE_TTL = timedelta(hours=1)
_FALLBACK_RATE = 90.0


async def get_usd_rub_rate() -> float:
    global _cache_rate, _cache_time

    if _cache_rate and _cache_time and datetime.utcnow() - _cache_time < _CACHE_TTL:
        return _cache_rate

    try:
        async with aiohttp.ClientSession() as client:
            async with client.get(
                "https://www.cbr.ru/scripts/XML_daily.asp",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                text = await resp.text(encoding="windows-1251")

        root = ET.fromstring(text)
        for valute in root.findall("Valute"):
            char_code = valute.find("CharCode")
            if char_code is not None and char_code.text == "USD":
                value = valute.find("Value")
                if value is not None:
                    _cache_rate = float(value.text.replace(",", "."))
                    _cache_time = datetime.utcnow()
                    return _cache_rate
    except Exception:
        pass

    return _cache_rate or _FALLBACK_RATE