import sqlite3
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
        status TEXT DEFAULT 'discovered'
    )
    """)

    conn.commit()
    conn.close()


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