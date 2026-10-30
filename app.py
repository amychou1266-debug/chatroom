from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)

# 初始化 SocketIO
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
)

# ===== 首頁 =====
@app.route("/")
def index():
    return render_template("index.html")


# 紀錄線上使用者
# { sid: {"username": str} }
clients = {}


# ===== SocketIO 事件處理區 =====

# 計算目前線上已設定使用者名稱的數量
def broadcast_user_count():
    socketio.emit(
        "user_count",
        {
            "count": len([
                c for c in clients.values()
                if c["username"]
            ])
        }
    )


# ===== 使用者連線 =====
@socketio.on("connect")
def on_connect():

    clients[request.sid] = {"username": None}

    print("Client connect:", request.sid)

    broadcast_user_count()


# ===== 使用者離線 =====
@socketio.on("disconnect")
def on_disconnect():

    # 從 clients 移除該用戶資訊
    info = clients.pop(request.sid, None)

    # 如果使用者有設定名稱，通知所有人
    if info and info["username"]:
        socketio.emit(
            "user_left",
            {
                "username": info["username"]
            }
        )

    # 更新線上人數
    broadcast_user_count()

    print("Client disconnect:", request.sid)


# ===== 設定使用者名稱 =====
@socketio.on("set_username")
def handle_set_username(data):

    username = str(data.get("username", "")).strip()

    if not username:
        return

    clients.setdefault(request.sid, {})["username"] = username

    broadcast_user_count()


# ===== 使用者加入聊天室 =====
@socketio.on("join")
def on_join(data):

    # 取得傳來的使用者名稱，預設為「匿名」
    username = data.get("username", "匿名")

    # 記錄使用者名稱
    clients.setdefault(request.sid, {})["username"] = username

    # 廣播通知所有人有新使用者加入
    socketio.emit(
        "user_joined",
        {
            "username": username
        }
    )

    # 更新線上人數
    broadcast_user_count()

    print(username, "joined")


# ===== 使用者傳送訊息 =====
@socketio.on("send_message")
def on_message(data):

    """
    將訊息廣播給其他使用者
    不包含自己，因為自己會先在畫面立即顯示
    """

    emit(
        "chat_message",
        data,
        broadcast=True,
        include_self=False
    )


# 使用者正在輸入時觸發
@socketio.on("typing")
def on_typing(data):
    # 廣播「某人正在輸入」的狀態給其他人（不含自己）
    emit("typing", data, broadcast=True, include_self=False)


# 使用者傳送訊息時觸發
# 使用者更改名稱時觸發
@socketio.on("change_username")
def on_change(data):
    old = data.get("oldUsername") # 原本的名稱
    new = data.get("newUsername") # 新名稱

    # 如果這個 SID 還在 clients 裡，更新名稱
    if request.sid in clients:
        clients[request.sid]["username"] = new

    # 廣播名稱變更事件給所有人
    emit("user_changed_name",
         {"oldUsername": old, "newUsername": new},
         broadcast=True)
# ===== 啟動 Flask =====
if __name__ == "__main__":

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True
    )