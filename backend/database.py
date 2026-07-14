import sqlite3
import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta

# Check for Render environment DB path (SQLite)
if os.environ.get("RENDER") == "true":
    os.makedirs("/var/data", exist_ok=True)
    DB_PATH = "/var/data/f1_dashboard.db"
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "f1_dashboard.db")

# Try initializing Firebase Firestore
USE_FIREBASE = False
db = None

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    
    cred_env = os.environ.get("FIREBASE_CREDENTIALS")
    cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firebase_credentials.json")
    
    if cred_env:
        # Load from Render/production environment variables as a JSON string
        cred_dict = json.loads(cred_env)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        USE_FIREBASE = True
        print("Firebase Firestore initialized successfully from credentials environment variable.")
    elif os.path.exists(cred_path):
        # Load from local JSON credentials file
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        USE_FIREBASE = True
        print("Firebase Firestore initialized successfully from local credentials file.")
except Exception as e:
    print(f"Firebase initialization skipped or failed: {e}. Falling back to SQLite.")

# ── SQLite Connections Helper ──────────────────────────────────────────────────

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── Database Initialization ───────────────────────────────────────────────────

def init_db():
    if USE_FIREBASE:
        print("Using Firebase Firestore. Dynamic initialization skipped (collections are auto-created).")
        return
        
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

# ── Password Hashing Helpers ──────────────────────────────────────────────────

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
    if USE_FIREBASE:
        try:
            # Check if username already exists
            query = db.collection("users").where("username", "==", username.strip()).limit(1).get()
            if len(query) > 0:
                return False
            
            # Determine next integer ID (retrieve highest current id)
            users = db.collection("users").get()
            next_id = 1
            if len(users) > 0:
                next_id = max([int(u.id) for u in users if u.id.isdigit()] + [0]) + 1
            
            user_data = {
                "id": next_id,
                "username": username.strip(),
                "password_hash": hash_password(password),
                "is_admin": 1 if is_admin else 0,
                "created_at": datetime.utcnow().isoformat()
            }
            db.collection("users").document(str(next_id)).set(user_data)
            return True
        except Exception as e:
            print(f"Firestore create_user error: {e}")
            return False
            
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
    if USE_FIREBASE:
        query = db.collection("users").where("username", "==", username.strip()).limit(1).get()
        if len(query) > 0:
            return query[0].to_dict()
        return None
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?;", (username.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: int):
    if USE_FIREBASE:
        doc = db.collection("users").document(str(user_id)).get()
        if doc.exists:
            return doc.to_dict()
        return None
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def verify_user_credentials(username: str, password: str):
    user = get_user_by_username(username)
    if user and verify_password(password, user['password_hash']):
        return user
    return None

# ── Admin Operations ──────────────────────────────────────────────────────────

def get_all_users():
    if USE_FIREBASE:
        users = db.collection("users").get()
        user_list = []
        for u in users:
            ud = u.to_dict()
            uid = ud['id']
            
            # Count chats and messages associated with this user
            chats = db.collection("chats").where("user_id", "==", uid).get()
            chat_ids = [c.id for c in chats]
            msg_count = 0
            if len(chat_ids) > 0:
                for cid in chat_ids:
                    msgs = db.collection("messages").where("chat_id", "==", cid).get()
                    msg_count += len(msgs)
                    
            user_list.append({
                "id": uid,
                "username": ud['username'],
                "is_admin": ud['is_admin'],
                "created_at": ud['created_at'],
                "chat_count": len(chats),
                "message_count": msg_count
            })
        user_list.sort(key=lambda x: x['created_at'], reverse=True)
        return user_list

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
    if USE_FIREBASE:
        try:
            # Check if username is taken by another user
            query = db.collection("users").where("username", "==", new_username.strip()).get()
            for q in query:
                if q.to_dict()['id'] != user_id:
                    return False
            
            doc_ref = db.collection("users").document(str(user_id))
            if doc_ref.get().exists:
                doc_ref.update({"username": new_username.strip()})
                return True
            return False
        except Exception:
            return False
            
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
    if USE_FIREBASE:
        new_hash = hash_password(new_password)
        doc_ref = db.collection("users").document(str(user_id))
        if doc_ref.get().exists:
            doc_ref.update({"password_hash": new_hash})
            return True
        return False

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
    if USE_FIREBASE:
        doc_ref = db.collection("users").document(str(user_id))
        if doc_ref.get().exists:
            doc_ref.delete()
            # Clean up chats and messages associated with this user
            chats = db.collection("chats").where("user_id", "==", user_id).get()
            for c in chats:
                db.collection("chats").document(c.id).delete()
                msgs = db.collection("messages").where("chat_id", "==", c.id).get()
                for m in msgs:
                    db.collection("messages").document(m.id).delete()
            return True
        return False

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?;", (user_id,))
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed

def admin_toggle_admin(user_id: int, make_admin: bool) -> bool:
    if USE_FIREBASE:
        doc_ref = db.collection("users").document(str(user_id))
        if doc_ref.get().exists:
            doc_ref.update({"is_admin": 1 if make_admin else 0})
            return True
        return False

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
    existing = get_user_by_username(username)
    if not existing:
        create_user(username, password, is_admin=True)
    elif not existing['is_admin']:
        if USE_FIREBASE:
            db.collection("users").document(str(existing['id'])).update({"is_admin": 1})
        else:
            conn = get_db_connection()
            conn.execute("UPDATE users SET is_admin = 1 WHERE username = ?;", (username,))
            conn.commit()
            conn.close()

# ── Session Operations ────────────────────────────────────────────────────────

def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    if USE_FIREBASE:
        db.collection("sessions").document(token).set({
            "token": token,
            "user_id": user_id,
            "expires_at": expires_at.isoformat()
        })
        return token

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
    if USE_FIREBASE:
        doc = db.collection("sessions").document(token).get()
        if doc.exists:
            sd = doc.to_dict()
            expires_at = datetime.fromisoformat(sd['expires_at'])
            if expires_at > datetime.utcnow():
                user = get_user_by_id(sd['user_id'])
                if user:
                    return {
                        "id": user['id'],
                        "username": user['username'],
                        "is_admin": bool(user['is_admin'])
                    }
            else:
                delete_session(token)
        return None

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
    if USE_FIREBASE:
        db.collection("sessions").document(token).delete()
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?;", (token,))
    conn.commit()
    conn.close()

# ── Chat Operations ───────────────────────────────────────────────────────────

def create_chat(user_id: int, chat_id: str, label: str):
    if USE_FIREBASE:
        try:
            doc_ref = db.collection("chats").document(chat_id)
            if doc_ref.get().exists:
                return False
            doc_ref.set({
                "id": chat_id,
                "user_id": user_id,
                "label": label,
                "created_at": datetime.utcnow().isoformat()
            })
            return True
        except Exception:
            return False

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
    if USE_FIREBASE:
        chats = db.collection("chats").where("user_id", "==", user_id).get()
        chat_list = [c.to_dict() for c in chats]
        chat_list.sort(key=lambda x: x['created_at'], reverse=True)
        return chat_list

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
    if USE_FIREBASE:
        doc_ref = db.collection("chats").document(chat_id)
        doc = doc_ref.get()
        if doc.exists and doc.to_dict()['user_id'] == user_id:
            doc_ref.delete()
            # Delete associated messages
            msgs = db.collection("messages").where("chat_id", "==", chat_id).get()
            for m in msgs:
                db.collection("messages").document(m.id).delete()
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chats WHERE id = ? AND user_id = ?;", (chat_id, user_id))
    conn.commit()
    conn.close()

def update_chat_label(user_id: int, chat_id: str, label: str):
    if USE_FIREBASE:
        doc_ref = db.collection("chats").document(chat_id)
        doc = doc_ref.get()
        if doc.exists and doc.to_dict()['user_id'] == user_id:
            doc_ref.update({"label": label})
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE chats SET label = ? WHERE id = ? AND user_id = ?;", (label, chat_id, user_id))
    conn.commit()
    conn.close()

# ── Message Operations ────────────────────────────────────────────────────────

def add_message(chat_id: str, role: str, content: str):
    if USE_FIREBASE:
        db.collection("messages").add({
            "chat_id": chat_id,
            "role": role,
            "content": content,
            "created_at": datetime.utcnow().isoformat()
        })
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?);",
        (chat_id, role, content)
    )
    conn.commit()
    conn.close()

def get_chat_messages(chat_id: str):
    if USE_FIREBASE:
        msgs = db.collection("messages").where("chat_id", "==", chat_id).get()
        msg_list = [m.to_dict() for m in msgs]
        msg_list.sort(key=lambda x: x['created_at'])
        return msg_list

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY created_at ASC;",
        (chat_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
