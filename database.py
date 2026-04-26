from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass

from config import Config


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredReview:
    author: str
    rating: int
    project: str
    text: str
    source: str


@dataclass(frozen=True)
class DatabaseStats:
    technical_specs: int
    reviews: int
    processed_emails: int


def _is_postgres(config: Config) -> bool:
    return bool(config.database_url)


@contextmanager
def _connect(config: Config):
    if _is_postgres(config):
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(config.database_url, row_factory=dict_row) as connection:
            yield connection
        return

    connection = sqlite3.connect(config.sqlite_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _adapt_query(config: Config, query: str) -> str:
    if _is_postgres(config):
        return query.replace("?", "%s").replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    return query


def init_database(config: Config) -> None:
    with _connect(config) as connection:
        for query in (
            """
            CREATE TABLE IF NOT EXISTS processed_emails (
                message_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                subject TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS technical_specs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                bot_type TEXT,
                features TEXT,
                deadline TEXT,
                budget TEXT,
                spec_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT NOT NULL,
                rating INTEGER NOT NULL,
                project TEXT,
                text TEXT NOT NULL,
                source TEXT DEFAULT 'Kwork',
                is_public INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
        ):
            connection.execute(_adapt_query(config, query))

    purge_fake_seed_reviews(config)
    logger.info("Database initialized: %s", "PostgreSQL" if _is_postgres(config) else f"SQLite {config.sqlite_path}")


def is_email_processed(config: Config, message_id: str) -> bool:
    with _connect(config) as connection:
        cursor = connection.execute(
            _adapt_query(config, "SELECT 1 FROM processed_emails WHERE message_id = ? LIMIT 1"),
            (message_id,),
        )
        return cursor.fetchone() is not None


def mark_email_processed(config: Config, message_id: str, event_type: str, subject: str) -> None:
    with _connect(config) as connection:
        query = """
        INSERT INTO processed_emails (message_id, event_type, subject)
        VALUES (?, ?, ?)
        """
        if _is_postgres(config):
            query += " ON CONFLICT (message_id) DO NOTHING"
        else:
            query = query.replace("INSERT INTO", "INSERT OR IGNORE INTO", 1)
        connection.execute(_adapt_query(config, query), (message_id, event_type, subject))


def save_technical_spec(
    config: Config,
    *,
    user_id: int | None,
    username: str,
    bot_type: str,
    features: str,
    deadline: str,
    budget: str,
    spec_text: str,
) -> None:
    with _connect(config) as connection:
        connection.execute(
            _adapt_query(
                config,
                """
                INSERT INTO technical_specs (user_id, username, bot_type, features, deadline, budget, spec_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
            ),
            (user_id, username, bot_type, features, deadline, budget, spec_text),
        )


def _rating(value) -> int:
    try:
        rating = int(value)
    except (TypeError, ValueError):
        rating = 5
    return max(1, min(5, rating))


def add_review(config: Config, *, author: str, rating: int, project: str, text: str, source: str = "Kwork") -> bool:
    author = author.strip() or "Клиент Kwork"
    project = project.strip()
    text = text.strip()
    source = source.strip() or "Kwork"
    if not text:
        return False

    with _connect(config) as connection:
        cursor = connection.execute(
            _adapt_query(config, "SELECT 1 FROM reviews WHERE author = ? AND text = ? LIMIT 1"),
            (author, text),
        )
        if cursor.fetchone() is not None:
            return False

        connection.execute(
            _adapt_query(
                config,
                """
                INSERT INTO reviews (author, rating, project, text, source, is_public)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
            ),
            (author, _rating(rating), project, text, source),
        )
        return True


def get_public_reviews(config: Config, limit: int = 8) -> list[StoredReview]:
    with _connect(config) as connection:
        cursor = connection.execute(
            _adapt_query(
                config,
                """
                SELECT author, rating, project, text, source
                FROM reviews
                WHERE is_public = 1
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
            ),
            (limit,),
        )
        rows = cursor.fetchall()

    return [
        StoredReview(
            author=row["author"],
            rating=_rating(row["rating"]),
            project=row["project"] or "",
            text=row["text"],
            source=row["source"] or "Kwork",
        )
        for row in rows
    ]


def purge_fake_seed_reviews(config: Config) -> int:
    fake_texts = (
        "Бот сделан аккуратно, все основные сценарии работают понятно. Заявки приходят в удобном формате.",
        "Получился удобный бот с каталогом и оформлением заказа. Константин помог продумать структуру и запуск.",
        "Хорошо собрана логика ответов и понятное меню. После теста быстро внесены правки.",
    )
    fake_projects = (
        "Telegram-бот для заявок",
        "Бот-магазин",
        "AI-ассистент",
    )

    deleted = 0
    with _connect(config) as connection:
        for text in fake_texts:
            cursor = connection.execute(
                _adapt_query(config, "DELETE FROM reviews WHERE text = ?"),
                (text,),
            )
            deleted += cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0

        for project in fake_projects:
            cursor = connection.execute(
                _adapt_query(
                    config,
                    """
                    DELETE FROM reviews
                    WHERE project = ?
                    AND author IN ('Клиент Kwork', 'РљР»РёРµРЅС‚ Kwork')
                    """,
                ),
                (project,),
            )
            deleted += cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0

    if deleted:
        logger.warning("Removed fake seed reviews from database. deleted=%s", deleted)
    return deleted


def get_stats(config: Config) -> DatabaseStats:
    with _connect(config) as connection:
        specs_count = connection.execute("SELECT COUNT(*) AS count FROM technical_specs").fetchone()["count"]
        reviews_count = connection.execute("SELECT COUNT(*) AS count FROM reviews WHERE is_public = 1").fetchone()["count"]
        emails_count = connection.execute("SELECT COUNT(*) AS count FROM processed_emails").fetchone()["count"]

    return DatabaseStats(
        technical_specs=int(specs_count),
        reviews=int(reviews_count),
        processed_emails=int(emails_count),
    )
