import sqlite3
from datetime import datetime
from config import DATABASE_PATH


VALID_EVENT_TYPES = {
    "discovered",
    "approved",
    "rejected",
    "generated",
    "dry_run_ready",
    "submitted",
    "failed",
    "note",
}


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_tracking_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS application_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        message TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(job_id) REFERENCES jobs(id)
    )
    """)

    conn.commit()
    conn.close()


def log_event(job_id, event_type, message=None):
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(
            f"Invalid event_type '{event_type}'. Valid types: {sorted(VALID_EVENT_TYPES)}"
        )

    init_tracking_db()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO application_events (job_id, event_type, message, created_at)
    VALUES (?, ?, ?, ?)
    """, (
        int(job_id),
        event_type,
        message,
        datetime.utcnow().isoformat(timespec="seconds"),
    ))

    conn.commit()
    conn.close()


def get_history(job_id):
    init_tracking_db()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT id, job_id, event_type, message, created_at
    FROM application_events
    WHERE job_id = ?
    ORDER BY created_at ASC, id ASC
    """, (int(job_id),))

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def print_history(job_id):
    events = get_history(job_id)

    if not events:
        print(f"No history found for job {job_id}.")
        return

    print(f"\nHistory for job {job_id}:")
    for event in events:
        msg = f" - {event['message']}" if event.get("message") else ""
        print(f"[{event['created_at']}] {event['event_type']}{msg}")
