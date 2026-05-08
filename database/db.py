import sqlite3
from datetime import datetime
from config import DATABASE_PATH


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        company TEXT,
        title TEXT,
        location TEXT,
        url TEXT UNIQUE,
        description TEXT,
        ats_job_id TEXT,
        fit_score INTEGER,
        status TEXT DEFAULT 'discovered',
        resume_path TEXT,
        cover_letter_path TEXT,
        application_packet_path TEXT,
        generated_at TEXT
    )
    """)

    existing_columns = get_existing_columns(cur, "jobs")

    migrations = {
        "resume_path": "ALTER TABLE jobs ADD COLUMN resume_path TEXT",
        "cover_letter_path": "ALTER TABLE jobs ADD COLUMN cover_letter_path TEXT",
        "application_packet_path": "ALTER TABLE jobs ADD COLUMN application_packet_path TEXT",
        "generated_at": "ALTER TABLE jobs ADD COLUMN generated_at TEXT",
    }

    for column, sql in migrations.items():
        if column not in existing_columns:
            cur.execute(sql)

    conn.commit()
    conn.close()


def get_existing_columns(cur, table_name):
    cur.execute(f"PRAGMA table_info({table_name})")
    return {row["name"] for row in cur.fetchall()}


def save_job(job):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO jobs
    (source, company, title, location, url, description, ats_job_id, fit_score, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job.get("source"),
        job.get("company"),
        job.get("title"),
        job.get("location"),
        job.get("url"),
        job.get("description"),
        str(job.get("ats_job_id")),
        job.get("fit_score"),
        job.get("status", "discovered")
    ))

    conn.commit()
    conn.close()


def get_jobs(status=None, limit=None):
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM jobs"
    params = []

    if status:
        query += " WHERE status = ?"
        params.append(status)

    query += " ORDER BY fit_score DESC"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    cur.execute(query, params)
    rows = [dict(row) for row in cur.fetchall()]

    conn.close()
    return rows


def get_job_by_id(job_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cur.fetchone()

    conn.close()
    return dict(row) if row else None


def update_job_status(job_id, status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    UPDATE jobs
    SET status = ?
    WHERE id = ?
    """, (status, job_id))

    conn.commit()
    conn.close()


def update_generated_files(job_id, resume_path, cover_letter_path, application_packet_path):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    UPDATE jobs
    SET resume_path = ?,
        cover_letter_path = ?,
        application_packet_path = ?,
        generated_at = ?,
        status = ?
    WHERE id = ?
    """, (
        resume_path,
        cover_letter_path,
        application_packet_path,
        datetime.utcnow().isoformat(),
        "generated",
        job_id
    ))

    conn.commit()
    conn.close()


def get_status_counts():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT status, COUNT(*) AS count
    FROM jobs
    GROUP BY status
    ORDER BY count DESC
    """)

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows