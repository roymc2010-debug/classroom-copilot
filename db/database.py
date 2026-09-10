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
    # Create table for push subscriptions (RFC 8291 Web Push)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            endpoint TEXT PRIMARY KEY,
            p256dh TEXT,
            auth TEXT,
            user_email TEXT,
            created_at TEXT
        )
    ''')
    # Create table to track tasks and announcements already notified/seen
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seen_classroom_items (
            item_id TEXT PRIMARY KEY,
            item_type TEXT,
            course_name TEXT,
            title TEXT,
            first_seen_at TEXT
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


def save_push_subscription(endpoint, p256dh, auth, user_email=""):
    conn = get_connection()
    cursor = conn.cursor()
    import datetime
    now_str = datetime.datetime.utcnow().isoformat()
    cursor.execute('''
        INSERT INTO push_subscriptions (endpoint, p256dh, auth, user_email, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(endpoint) DO UPDATE SET
            p256dh = excluded.p256dh,
            auth = excluded.auth,
            user_email = excluded.user_email
    ''', (endpoint, p256dh, auth, user_email.lower().strip(), now_str))
    conn.commit()
    conn.close()

def delete_push_subscription(endpoint):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))
    conn.commit()
    conn.close()

def get_push_subscriptions_for_user(user_email=""):
    conn = get_connection()
    cursor = conn.cursor()
    norm_email = (user_email or "").lower().strip()
    if norm_email:
        cursor.execute("SELECT endpoint, p256dh, auth, user_email FROM push_subscriptions WHERE user_email = ? OR user_email = ''", (norm_email,))
    else:
        cursor.execute("SELECT endpoint, p256dh, auth, user_email FROM push_subscriptions")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "endpoint": r["endpoint"],
            "keys": {
                "p256dh": r["p256dh"],
                "auth": r["auth"]
            },
            "user_email": r["user_email"]
        }
        for r in rows
    ]

def get_all_push_subscriptions():
    return get_push_subscriptions_for_user("")

def is_item_seen(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM seen_classroom_items WHERE item_id = ?", (str(item_id),))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def get_seen_item_ids():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT item_id FROM seen_classroom_items")
    rows = cursor.fetchall()
    conn.close()
    return {r["item_id"] for r in rows}

def mark_item_seen(item_id, item_type="task", course_name="", title=""):
    conn = get_connection()
    cursor = conn.cursor()
    import datetime
    now_str = datetime.datetime.utcnow().isoformat()
    cursor.execute('''
        INSERT INTO seen_classroom_items (item_id, item_type, course_name, title, first_seen_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(item_id) DO NOTHING
    ''', (str(item_id), item_type, course_name, title, now_str))
    conn.commit()
    conn.close()

def mark_items_seen_bulk(items):
    """items: list of dicts with keys item_id, item_type, course_name, title"""
    if not items:
        return
    conn = get_connection()
    cursor = conn.cursor()
    import datetime
    now_str = datetime.datetime.utcnow().isoformat()
    cursor.executemany('''
        INSERT INTO seen_classroom_items (item_id, item_type, course_name, title, first_seen_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(item_id) DO NOTHING
    ''', [(str(it["item_id"]), it.get("item_type", "task"), it.get("course_name", ""), it.get("title", ""), now_str) for it in items])
    conn.commit()
    conn.close()

# Initialize the database on module import
init_db()

