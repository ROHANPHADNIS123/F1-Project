import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Firestore
cred_env = os.environ.get("FIREBASE_CREDENTIALS")
cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firebase_credentials.json")

if not firebase_admin._apps:
    if cred_env:
        cred_dict = json.loads(cred_env)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    elif os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        raise RuntimeError(
            "Firebase Firestore credentials not found! Set the FIREBASE_CREDENTIALS environment variable "
            "or place 'firebase_credentials.json' in the backend directory."
        )

db = firestore.client()

def init_db():
    """No-op for Firebase as collections are auto-created when writing documents."""
    print("Firebase Firestore initialized.")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, stored_hash: str) -> bool:
    return hash_password(password) == stored_hash

def create_user(username: str, password: str, is_admin: bool = False) -> bool:
    try:
        # Check if username exists
        query = db.collection("users").where("username", "==", username.strip()).limit(1).get()
        if len(query) > 0:
            return False
            
        # Get next ID auto-increment style (simple count)
        users = db.collection("users").get()
        next_id = len(users) + 1
        
        hashed = hash_password(password)
        user_data = {
            "id": next_id,
            "username": username.strip(),
            "password_hash": hashed,
            "is_admin": 1 if is_admin else 0,
            "created_at": datetime.utcnow().isoformat()
        }
        db.collection("users").document(str(next_id)).set(user_data)
        return True
    except Exception as e:
        print(f"Firestore create_user error: {e}")
        return False

def get_user_by_username(username: str):
    try:
        query = db.collection("users").where("username", "==", username.strip()).limit(1).get()
        if len(query) > 0:
            return query[0].to_dict()
    except Exception as e:
        print(f"Firestore get_user_by_username error: {e}")
    return None

def get_user_by_id(user_id: int):
    try:
        doc = db.collection("users").document(str(user_id)).get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        print(f"Firestore get_user_by_id error: {e}")
    return None

def verify_user_credentials(username: str, password: str):
    user = get_user_by_username(username)
    if user and verify_password(password, user['password_hash']):
        return user
    return None

def get_all_users():
    try:
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
    except Exception as e:
        print(f"Firestore get_all_users error: {e}")
        return []

def admin_update_username(user_id: int, new_username: str) -> bool:
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
    except Exception as e:
        print(f"Firestore admin_update_username error: {e}")
        return False

def admin_update_password(user_id: int, new_password: str) -> bool:
    try:
        new_hash = hash_password(new_password)
        doc_ref = db.collection("users").document(str(user_id))
        if doc_ref.get().exists:
            doc_ref.update({"password_hash": new_hash})
            return True
        return False
    except Exception as e:
        print(f"Firestore admin_update_password error: {e}")
        return False

def admin_delete_user(user_id: int) -> bool:
    try:
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
    except Exception as e:
        print(f"Firestore admin_delete_user error: {e}")
        return False

def admin_toggle_admin(user_id: int, make_admin: bool) -> bool:
    try:
        doc_ref = db.collection("users").document(str(user_id))
        if doc_ref.get().exists:
            doc_ref.update({"is_admin": 1 if make_admin else 0})
            return True
        return False
    except Exception as e:
        print(f"Firestore admin_toggle_admin error: {e}")
        return False

def ensure_admin_exists(username: str, password: str):
    try:
        existing = get_user_by_username(username)
        if not existing:
            create_user(username, password, is_admin=True)
        elif not existing['is_admin']:
            db.collection("users").document(str(existing['id'])).update({"is_admin": 1})
    except Exception as e:
        print(f"Firestore ensure_admin_exists error: {e}")

def create_session(user_id: int) -> str:
    try:
        token = secrets.token_hex(32)
        expires_at = datetime.utcnow() + timedelta(days=7)
        db.collection("sessions").document(token).set({
            "token": token,
            "user_id": user_id,
            "expires_at": expires_at.isoformat()
        })
        return token
    except Exception as e:
        print(f"Firestore create_session error: {e}")
        return ""

def verify_session(token: str):
    try:
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
    except Exception as e:
        print(f"Firestore verify_session error: {e}")
    return None

def delete_session(token: str):
    try:
        db.collection("sessions").document(token).delete()
    except Exception as e:
        print(f"Firestore delete_session error: {e}")

def create_chat(user_id: int, chat_id: str, label: str):
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
    except Exception as e:
        print(f"Firestore create_chat error: {e}")
        return False

def get_user_chats(user_id: int):
    try:
        chats = db.collection("chats").where("user_id", "==", user_id).get()
        chat_list = [c.to_dict() for c in chats]
        chat_list.sort(key=lambda x: x['created_at'], reverse=True)
        return chat_list
    except Exception as e:
        print(f"Firestore get_user_chats error: {e}")
        return []

def delete_chat(user_id: int, chat_id: str):
    try:
        doc_ref = db.collection("chats").document(chat_id)
        doc = doc_ref.get()
        if doc.exists and doc.to_dict()['user_id'] == user_id:
            doc_ref.delete()
            # Delete associated messages
            msgs = db.collection("messages").where("chat_id", "==", chat_id).get()
            for m in msgs:
                db.collection("messages").document(m.id).delete()
    except Exception as e:
        print(f"Firestore delete_chat error: {e}")

def update_chat_label(user_id: int, chat_id: str, label: str):
    try:
        doc_ref = db.collection("chats").document(chat_id)
        doc = doc_ref.get()
        if doc.exists and doc.to_dict()['user_id'] == user_id:
            doc_ref.update({"label": label})
    except Exception as e:
        print(f"Firestore update_chat_label error: {e}")

def add_message(chat_id: str, role: str, content: str):
    try:
        db.collection("messages").add({
            "chat_id": chat_id,
            "role": role,
            "content": content,
            "created_at": datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"Firestore add_message error: {e}")

def get_chat_messages(chat_id: str):
    try:
        msgs = db.collection("messages").where("chat_id", "==", chat_id).get()
        msg_list = [m.to_dict() for m in msgs]
        msg_list.sort(key=lambda x: x['created_at'])
        return msg_list
    except Exception as e:
        print(f"Firestore get_chat_messages error: {e}")
        return []
