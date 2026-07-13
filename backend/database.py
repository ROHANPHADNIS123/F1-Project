import sqlite3
import os
import hashlib
import secrets
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "f1_dashboard.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Create users table (with is_admin flag)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Migrate existing tables that don't have is_admin yet
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0;")
    except Exception:
        pass  # Column already exists
    
    # Create chats table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        label TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    
    # Create messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
    );
    """)
    
    # Create sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    
    conn.commit()
    conn.close()

# Password Hashing Helpers using native pbkdf2_hmac
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ":" + pwdhash.hex()

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return pwdhash == expected_hash
    except Exception:
        return False

# ── User Operations ──────────────────────────────────────────────────────────

def create_user(username: str, password: str, is_admin: bool = False) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed = hash_password(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?);",
            (username.strip(), hashed, 1 if is_admin else 0)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_username(username: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?;", (username.strip(),))
    row = cursor.fetchone()
    conn.close()
    return row

def get_user_by_id(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def verify_user_credentials(username: str, password: str):
    user = get_user_by_username(username)
    if user and verify_password(password, user['password_hash']):
        return user
    return None

# ── Admin Operations ──────────────────────────────────────────────────────────

def get_all_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.username, u.is_admin, u.created_at,
               COUNT(DISTINCT c.id) AS chat_count,
               COUNT(DISTINCT m.id) AS message_count
        FROM users u
        LEFT JOIN chats c ON c.user_id = u.id
        LEFT JOIN messages m ON m.chat_id = c.id
        GROUP BY u.id
        ORDER BY u.created_at DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def admin_update_username(user_id: int, new_username: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET username = ? WHERE id = ?;",
            (new_username.strip(), user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def admin_update_password(user_id: int, new_password: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    new_hash = hash_password(new_password)
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?;",
        (new_hash, user_id)
    )
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed

def admin_delete_user(user_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?;", (user_id,))
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed

def admin_toggle_admin(user_id: int, make_admin: bool) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET is_admin = ? WHERE id = ?;",
        (1 if make_admin else 0, user_id)
    )
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed

def ensure_admin_exists(username: str, password: str):
    """Seed the admin account if it doesn't exist yet."""
    existing = get_user_by_username(username)
    if not existing:
        create_user(username, password, is_admin=True)
    elif not existing['is_admin']:
        # Upgrade existing user to admin
        conn = get_db_connection()
        conn.execute("UPDATE users SET is_admin = 1 WHERE username = ?;", (username,))
        conn.commit()
        conn.close()

# ── Session Operations ────────────────────────────────────────────────────────

def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?);",
        (token, user_id, expires_at.isoformat())
    )
    conn.commit()
    conn.close()
    return token

def verify_session(token: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sessions.user_id, users.username, users.is_admin, sessions.expires_at "
        "FROM sessions JOIN users ON sessions.user_id = users.id WHERE token = ?;",
        (token,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        expires_at = datetime.fromisoformat(row['expires_at'])
        if expires_at > datetime.utcnow():
            return {
                "id": row['user_id'],
                "username": row['username'],
                "is_admin": bool(row['is_admin'])
            }
        else:
            delete_session(token)
    return None

def delete_session(token: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?;", (token,))
    conn.commit()
    conn.close()

# ── Chat Operations ───────────────────────────────────────────────────────────

def create_chat(user_id: int, chat_id: str, label: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO chats (id, user_id, label) VALUES (?, ?, ?);",
            (chat_id, user_id, label)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_chats(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, label, created_at FROM chats WHERE user_id = ? ORDER BY created_at DESC;",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_chat(user_id: int, chat_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chats WHERE id = ? AND user_id = ?;", (chat_id, user_id))
    conn.commit()
    conn.close()

def update_chat_label(user_id: int, chat_id: str, label: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE chats SET label = ? WHERE id = ? AND user_id = ?;", (label, chat_id, user_id))
    conn.commit()
    conn.close()

# ── Message Operations ────────────────────────────────────────────────────────

def add_message(chat_id: str, role: str, content: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?);",
        (chat_id, role, content)
    )
    conn.commit()
    conn.close()

def get_chat_messages(chat_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY created_at ASC;",
        (chat_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
