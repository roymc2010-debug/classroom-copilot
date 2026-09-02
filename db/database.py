import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "classroom_tasks.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Create table for task state.
    # id corresponds to the Google Classroom assignment id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_state (
            id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'pending',
            notes TEXT DEFAULT ''
        )
    ''')
    conn.commit()
    conn.close()

def get_task_state(task_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, notes FROM task_state WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"status": "pending", "notes": ""}

def get_all_task_states():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, notes FROM task_state")
    rows = cursor.fetchall()
    conn.close()
    return {row["id"]: {"status": row["status"], "notes": row["notes"]} for row in rows}

def update_task_status(task_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO task_state (id, status)
        VALUES (?, ?)
        ON CONFLICT(id) DO UPDATE SET status = excluded.status
    ''', (task_id, status))
    conn.commit()
    conn.close()

def update_task_notes(task_id, notes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO task_state (id, notes)
        VALUES (?, ?)
        ON CONFLICT(id) DO UPDATE SET notes = excluded.notes
    ''', (task_id, notes))
    conn.commit()
    conn.close()

# Initialize the database on module import
init_db()
