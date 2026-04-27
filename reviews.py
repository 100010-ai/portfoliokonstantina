from __future__ import annotations

import html
import logging
import time

from config import Config
from database import get_public_reviews


logger = logging.getLogger(__name__)
_CACHE_TTL_SECONDS = 300
_cache_text = ""
_cache_expires_at = 0.0


def build_reviews_text(config: Config) -> str:
    global _cache_expires_at, _cache_text

    now = time.monotonic()
    if _cache_text and now < _cache_expires_at:
        return _cache_text

    try:
        reviews = get_public_reviews(config)
    except Exception:
        logger.exception("Could not load reviews.")
        _cache_text = (
            "<b>⭐ Отзывы клиентов</b>\n\n"
            "⚠️ Сейчас раздел временно недоступен. Попробуйте открыть его чуть позже."
        )
        _cache_expires_at = now + 60
        return _cache_text

    if not reviews:
        _cache_text = (
            "<b>⭐ Отзывы клиентов</b>\n\n"
            "Пока отзывов в базе нет. Когда отзывы подтянутся с Kwork или будут добавлены администратором, "
            "они появятся здесь 🙂"
        )
        _cache_expires_at = now + _CACHE_TTL_SECONDS
        return _cache_text

    blocks = [
        "<b>⭐ Отзывы клиентов</b>",
        "<i>Показываю свежие публичные отзывы с Kwork и добавленные вручную реальные отзывы.</i>",
    ]
    for index, review in enumerate(reviews, start=1):
        stars = "★" * review.rating + "☆" * (5 - review.rating)
        project = f"\n📌 <b>Проект:</b> {html.escape(review.project)}" if review.project else ""
        review_text = review.text if len(review.text) <= 320 else f"{review.text[:317].rstrip()}..."
        blocks.append(
            f"""
<b>{index}. {html.escape(review.author)}</b>
⭐ <b>Оценка:</b> {stars}{project}
🔎 <b>Источник:</b> {html.escape(review.source)}

<i>{html.escape(review_text)}</i>
""".strip()
        )

    _cache_text = "\n\n".join(blocks)
    _cache_expires_at = now + _CACHE_TTL_SECONDS
    return _cache_text


def clear_reviews_cache() -> None:
    global _cache_expires_at, _cache_text
    _cache_text = ""
    _cache_expires_at = 0.0
