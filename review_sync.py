from __future__ import annotations

import asyncio
import html
import json
import logging
import re
import urllib.request
from dataclasses import dataclass
from typing import Any

from config import Config
from database import add_review


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedReview:
    author: str
    rating: int
    project: str
    text: str
    source: str = "Kwork"


def _reviews_url(config: Config) -> str:
    return config.kwork_reviews_url or config.kwork_profile_url or config.kwork_bot_service_url


def is_configured(config: Config) -> bool:
    url = _reviews_url(config)
    return url.startswith(("http://", "https://"))


def _fetch_page(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; PortfolioBot/1.0; +https://telegram.org/bot)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _rating(value: Any) -> int:
    try:
        rating = int(float(value))
    except (TypeError, ValueError):
        rating = 5
    return max(1, min(5, rating))


def _clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _walk_json(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _extract_json_ld(page: str) -> list[Any]:
    blocks = re.findall(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        page,
        flags=re.IGNORECASE | re.DOTALL,
    )
    parsed: list[Any] = []
    for block in blocks:
        try:
            parsed.append(json.loads(html.unescape(block).strip()))
        except json.JSONDecodeError:
            logger.debug("Could not parse JSON-LD block from reviews page.")
    return parsed


def _review_from_json(item: dict[str, Any]) -> ParsedReview | None:
    item_type = item.get("@type") or item.get("type")
    if isinstance(item_type, list):
        is_review = any(str(value).lower() == "review" for value in item_type)
    else:
        is_review = str(item_type).lower() == "review"
    if not is_review:
        return None

    text = _clean_text(item.get("reviewBody") or item.get("description") or item.get("text"))
    if len(text) < 15:
        return None

    author_raw = item.get("author")
    if isinstance(author_raw, dict):
        author = _clean_text(author_raw.get("name"))
    else:
        author = _clean_text(author_raw)

    rating_raw = item.get("reviewRating")
    if isinstance(rating_raw, dict):
        rating = _rating(rating_raw.get("ratingValue") or rating_raw.get("value"))
    else:
        rating = _rating(rating_raw)

    item_reviewed = item.get("itemReviewed")
    project = ""
    if isinstance(item_reviewed, dict):
        project = _clean_text(item_reviewed.get("name"))
    project = project or _clean_text(item.get("name"))

    return ParsedReview(
        author=author or "Клиент Kwork",
        rating=rating,
        project=project,
        text=text,
    )


def parse_reviews_from_page(page: str) -> list[ParsedReview]:
    reviews: list[ParsedReview] = []

    for json_block in _extract_json_ld(page):
        for item in _walk_json(json_block):
            review = _review_from_json(item)
            if review:
                reviews.append(review)

    if not reviews:
        for text in re.findall(r'"reviewBody"\s*:\s*"([^"]{20,1000})"', page):
            reviews.append(ParsedReview(author="Клиент Kwork", rating=5, project="", text=_clean_text(text)))

    unique: dict[tuple[str, str], ParsedReview] = {}
    for review in reviews:
        unique[(review.author.lower(), review.text.lower())] = review
    return list(unique.values())[:20]


def sync_reviews_once(config: Config) -> int:
    if not is_configured(config):
        logger.info("Kwork reviews sync is disabled: no valid public Kwork URL configured.")
        return 0

    page = _fetch_page(_reviews_url(config))
    parsed_reviews = parse_reviews_from_page(page)
    added_count = 0

    for review in parsed_reviews:
        if add_review(
            config,
            author=review.author,
            rating=review.rating,
            project=review.project,
            text=review.text,
            source=review.source,
        ):
            added_count += 1

    logger.info("Kwork reviews sync finished. Parsed=%s Added=%s", len(parsed_reviews), added_count)
    return added_count


async def start_reviews_sync(config: Config) -> None:
    if not is_configured(config):
        logger.info("Kwork reviews sync is disabled")
        return

    logger.info("Kwork reviews sync started")
    while True:
        await asyncio.sleep(config.reviews_sync_interval)
        try:
            await asyncio.to_thread(sync_reviews_once, config)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Could not sync Kwork reviews.")
