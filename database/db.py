import sqlite3
from config import DATABASE_PATH

def get_connection():
    return sqlite3.connect(DATABASE_PATH)

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

def get_jobs():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs ORDER BY fit_score DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows
