# from flask import Flask
# from flask_socketio import SocketIO

# app = Flask(__name__)
# socketio = SocketIO(
#     app, 
#     cors_allowed_origins="*",
#     async_mode="eventlet",
#     transports=["websocket"]
# )

# if __name__ == '__main__':
#     socketio.run(app, host="0.0.0.0", port=5000)


from flask import Flask
from socketio_instance import socketio  # 동일한 SocketIO 객체 불러오기

app = Flask(__name__)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000)
