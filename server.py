import socket
import threading
import os
import sqlite3
import datetime
from cryptography.fernet import Fernet

# ===== 設定 =====
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 12345))
KEY = b"YHQpkfNfwJxiJ1VW_KW2IKs4rBbGmHuR7qskYjimFo4="

fernet = Fernet(KEY)

clients = {}
lock = threading.Lock()

# ===== DB =====
db = sqlite3.connect("history.db", check_same_thread=False)
cur = db.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    content TEXT,
    created_at TEXT
)
""")
db.commit()

def save_message(user, msg):
    cur.execute(
        "INSERT INTO messages VALUES (NULL,?,?,?)",
        (user, msg, datetime.datetime.now().isoformat())
    )
    db.commit()

def broadcast(data, sender=None):
    with lock:
        for u, c in list(clients.items()):
            if u != sender:
                try:
                    c.sendall(data)
                except:
                    pass

def handle_client(conn):
    username = None
    try:
        # USERNAME 要求
        conn.sendall(fernet.encrypt(b"USERNAME"))

        username = fernet.decrypt(conn.recv(2048)).decode()

        with lock:
            if username in clients:
                conn.close()
                return
            clients[username] = conn

        broadcast(
            fernet.encrypt(f"[SYSTEM] {username} joined\n".encode()),
            sender=username
        )

        while True:
            data = conn.recv(4096)
            if not data:
                break

            text = fernet.decrypt(data).decode()
            save_message(username, text)

            broadcast(
                fernet.encrypt(f"{username}: {text}\n".encode()),
                sender=username
            )

    except:
        pass
    finally:
        with lock:
            if username in clients:
                del clients[username]

        broadcast(
            fernet.encrypt(f"[SYSTEM] {username} left\n".encode())
        )
        conn.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(10)
    print(f"Server listening on {PORT}", flush=True)

    while True:
        conn, _ = server.accept()
        threading.Thread(
            target=handle_client,
            args=(conn,),
            daemon=True
        ).start()

if __name__ == "__main__":
    main()
