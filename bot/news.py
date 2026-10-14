"""Small GDELT DOC client for recent headlines."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx


GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


@dataclass(frozen=True)
class NewsRequest:
    label: str
    query: str


@dataclass(frozen=True)
class Article:
    title: str
    url: str
    source: str
    language: str
    published: str


REGIONS = {
    "росси": ("Россия", "sourcecountry:russia"),
    "сша": ("США", "sourcecountry:unitedstates"),
    "америк": ("США", "sourcecountry:unitedstates"),
    "кита": ("Китай", "sourcecountry:china"),
    "украин": ("Украина", "sourcecountry:ukraine"),
    "британ": ("Великобритания", "sourcecountry:unitedkingdom"),
    "инд": ("Индия", "sourcecountry:india"),
    "япон": ("Япония", "sourcecountry:japan"),
    "коре": ("Южная Корея", "sourcecountry:southkorea"),
    "европ": ("Европа", "(sourcecountry:france OR sourcecountry:germany OR sourcecountry:italy OR sourcecountry:spain)"),
    "мир": ("мир", ""),
}
TOPICS = {
    "полит": ("политика", '(politics OR election OR government OR parliament OR president)'),
    "ии": ("искусственный интеллект", '("artificial intelligence" OR AI)'),
    "искусственн": ("искусственный интеллект", '("artificial intelligence" OR AI)'),
    "нейросет": ("нейросети", '(AI OR "machine learning" OR neural network)'),
    "желез": ("компьютерное железо", '(GPU OR processor OR chip OR hardware)'),
    "видеокарт": ("видеокарты", '(GPU OR graphics card OR NVIDIA OR AMD)'),
    "сервер": ("серверы и дата-центры", '(server OR datacenter OR data center)'),
    "чип": ("чипы и процессоры", '(chip OR semiconductor OR processor)'),
    "технолог": ("технологии", '(technology OR tech OR innovation)'),
    "программ": ("программирование", '(software OR programming OR developer OR cybersecurity)'),
    "кибербезопас": ("кибербезопасность", '(cybersecurity OR cyberattack OR ransomware)'),
    "компьютер": ("компьютеры", '(computer OR PC OR laptop OR hardware)'),
    "процессор": ("процессоры", '(processor OR CPU OR semiconductor)'),
    "эконом": ("экономика", '(economy OR inflation OR market OR trade)'),
    "наук": ("наука", '(science OR research OR discovery)'),
    "космос": ("космос", '(space OR NASA OR astronomy OR satellite)'),
    "мобильн": ("смартфоны и мобильные технологии", '(smartphone OR mobile phone OR Android OR iPhone)'),
    "ai": ("искусственный интеллект", '("artificial intelligence" OR AI)'),
}


def parse_news_request(text: str) -> NewsRequest | None:
    """Return a safe, predefined GDELT query when the user asks for news."""
    value = text.lower().replace("ё", "е")
    value = re.sub(r"(.)\1{2,}", r"\1\1", value, flags=re.UNICODE)
    if not re.search(
        r"\b(новост\w*|news|headlines?|что в мире|что происходит|сводк\w*|дайджест\w*|заголовк\w*|"
        r"последние события|свежие события|последние новости|что нового|что там нового|события дня|"
        r"what'?s happening|what is happening|latest updates)\b",
        value,
    ):
        return None

    region_name, region_query = "мир", ""
    for key, (name, query) in REGIONS.items():
        if key in value:
            region_name, region_query = name, query
            break

    topic_name, topic_query = "главное", ""
    for key, (name, query) in TOPICS.items():
        matched = bool(re.search(r"(?<![а-яa-z])" + re.escape(key) + r"(?![а-яa-z])", value)) if key in {"ии", "ai"} else key in value
        if matched:
            topic_name, topic_query = name, query
            break

    parts = [item for item in (region_query, topic_query) if item]
    query = " ".join(parts) or '(news OR politics OR economy OR technology OR conflict)'
    return NewsRequest(label=f"{topic_name.capitalize()} — {region_name}", query=query)


async def fetch_news(request: NewsRequest, *, limit: int = 8) -> list[Article]:
    params = {
        "query": request.query,
        "mode": "artlist",
        "format": "json",
        "timespan": "24h",
        "maxrecords": str(limit),
        "sort": "datedesc",
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0), follow_redirects=True) as client:
        response = await client.get(GDELT_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    articles: list[Article] = []
    seen: set[str] = set()
    for row in payload.get("articles", []):
        if not isinstance(row, dict):
            continue
        title = str(row.get("title", "")).strip()
        url = str(row.get("url", "")).strip()
        if not title or not url or url in seen:
            continue
        seen.add(url)
        raw_date = str(row.get("seendate", ""))
        published = _format_date(raw_date)
        articles.append(
            Article(
                title=title,
                url=url,
                source=str(row.get("domain", "Источник")).strip() or "Источник",
                language=str(row.get("language", "")).strip(),
                published=published,
            )
        )
    return articles


def _format_date(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return parsed.astimezone().strftime("%d.%m %H:%M")
    except ValueError:
        return value or "время неизвестно"
