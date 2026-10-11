import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json

load_dotenv()


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "rag_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def save_ticket(result):
    query = """
        INSERT INTO support_tickets (
            ticket_text,
            category,
            sentiment,
            risk_level,
            priority,
            action,
            needs_human_review,
            reason,
            draft_reply,
            sources
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    result.get("ticket", ""),
                    result.get("category", "human_review"),
                    result.get("sentiment", "neutral"),
                    result.get("risk_level", "low"),
                    result.get("priority", "normal"),
                    result.get("action", "HUMAN_REVIEW"),
                    result.get("needs_human_review", True),
                    result.get("reason", ""),
                    result.get("draft_reply", ""),
                    Json(result.get("sources", [])),
                ),
            )

            ticket_id = cur.fetchone()[0]

    return ticket_id