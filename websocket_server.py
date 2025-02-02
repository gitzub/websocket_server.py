# websocket_server.py (Railway 서버)
from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)

# SocketIO 객체를 직접 생성 (이전에는 socketio_instance.py에서 가져옴)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",  # 모든 오리진 허용
    transports=["websocket"]  # WebSocket 전송 방식 사용
)

if __name__ == '__main__':
    # WebSocket 서버 실행
    socketio.run(app, host="0.0.0.0", port=5000)  # 외부에서 접근 가능하도록 설정


# from flask import Flask
# from socketio_instance import socketio  # 동일한 SocketIO 객체 불러오기

# app = Flask(__name__)

# if __name__ == '__main__':
#     socketio.run(app, host="0.0.0.0", port=5000)
