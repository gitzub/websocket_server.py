# websocket_server.py (Railway 서버)

# from flask import Flask
# from socketio_instance import socketio  # 동일한 SocketIO 객체 불러오기

# app = Flask(__name__)

# if __name__ == '__main__':
#     socketio.run(app, host="0.0.0.0", port=5000)

import os
from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)

# SocketIO 객체를 직접 생성 (이전에는 socketio_instance.py에서 가져옴)
socketio = SocketIO(
    app,
    cors_allowed_origins="https://websocketserverpy-production.up.railway.app",  # 모든 오리진 허용
    transports=["websocket"]  # WebSocket 전송 방식 사용
)


# SocketIO 이벤트 등록 함수
# def register_socketio_events(socketio):
def register_socketio_events(sio: SocketIO):
    global socketio  # socketio 전역 변수로 설정
    socketio = sio

    @socketio.on_error()  # 모든 이벤트에서 발생하는 에러를 처리
    def handle_error(e):
        print(f"에러 발생: {e}")

    # @socketio.on("connect")
    # def handle_connect():
    #     # 클라이언트가 연결될 때 방 목록을 전송합니다.
    #     print("클라이언트가 연결되었습니다.")
    #     rooms = app.mongo.db.GameOmok.find({"state": {"$in": ["대기중", "진행중"]}})
    #     # MongoDB에서 가져온 데이터를 JSON 형식으로 변환
    #     rooms_list = []
    #     for room in rooms:
    #         room_data = {
    #             "room_name": room.get("room_name"),
    #             "state": room.get("state"),
    #             "_id": str(room.get("_id")),  # _id를 문자열로 변환
    #         }
    #         rooms_list.append(room_data)
    #     emit("update_rooms", rooms_list)

    @socketio.on("connect")
    def handle_connect():
        print("클라이언트가 연결되었습니다.")
        try:
            rooms = app.mongo.db.GameOmok.find({"state": {"$in": ["대기중", "진행중"]}})
            rooms_list = []
            for room in rooms:
                room_data = {
                    "room_name": room.get("room_name"),
                    "state": room.get("state"),
                    "_id": str(room.get("_id")),
                }
                rooms_list.append(room_data)
            emit("update_rooms", rooms_list)
        except Exception as e:
            print("에러 발생:", e)

    # WebSocket 연결 및 게임 시작
    @socketio.on("join")
    def on_join(data):
        # 애플리케이션 컨텍스트를 명시적으로 활성화
        # with app.app_context():
        #     print("조인 실행 데이타", data)

        # game_active_omok = True

        # Flask 애플리케이션 컨텍스트 내에서 작업을 보장합니다.
        # with app.app_context():
        #     # 애플리케이션 컨텍스트 내에서 socketio를 안전하게 사용할 수 있습니다.
        #     socketio = app.extensions.get("socketio")

        room_id = data["room_id"]
        nickname = data["nickname"]

        user = app.mongo.db.Users.find_one({"nickname": nickname})
        user_id = user["_id"]

        room = app.mongo.db.GameOmok.find_one({"_id": ObjectId(room_id)})

        print("닉네임", {nickname})
        print("룸아이디", {room_id})

        # 클라이언트가 방에 참가
        join_room(room_id)
        print(f"플레이어 {nickname}가 방 {room_id}에 참가했습니다.")

        # **blackstone과 whitestone 값 보내기**
        blackstone_id = room["blackstone"]
        whitestone_id = room["whitestone"]

        # blackstone과 whitestone의 닉네임을 가져옴
        blackstone_user = app.mongo.db.Users.find_one({"_id": blackstone_id})
        whitestone_user = app.mongo.db.Users.find_one({"_id": whitestone_id})

        blackstone_nickname = (
            blackstone_user["nickname"] if blackstone_user else "대기중"
        )
        whitestone_nickname = (
            whitestone_user["nickname"] if whitestone_user else "대기중"
        )

        # 방에 있는 blackstone과 whitestone 값을 소켓으로 전송
        socketio.emit(
            "room_user_stone_info",
            {
                "state": room["state"],
                "blackstone": str(blackstone_id),
                "whitestone": str(whitestone_id),
                "blackstone_nickname": blackstone_nickname,
                "whitestone_nickname": whitestone_nickname,
            },
            room=room_id,
        )

        # 방이 존재하지 않으면 처리
        if room is None:
            return "방을 찾을 수 없습니다.", 404

        if not room:
            print(f"Invalid room_id on_join: {room_id}")
            return

        # 보드 상태 가져오기
        board = room.get(
            "board", [[None] * 15 for _ in range(15)]
        )  # 보드 정보가 없으면 빈 15x15 배열을 사용

        # 방에 참가한 후, 해당 방에 있는 모든 클라이언트에게 이벤트 전송
        emit(
            "game_update",
            {
                "state": room["state"],
                # "current_turn": room["current_turn"],
                # "player_color": (
                #     "black" if room["playerA"] is None else "white"
                # ),  # 흑/백 구분
                "board": board,  # 보드 상태 전달
            },
            room=room_id,
        )

    @socketio.on("make_move")
    def make_move(data):
        print("메이크무브 실행")

        # game_active_omok = True

        room_id = data["room_id"]
        row = data["row"]
        col = data["col"]
        player = data["player"]

        print(
            f"make_move 이벤트 받음: room_id={room_id}, row={row}, col={col}, player={player}"
        )  # 로그 추가

        # room 조회
        room = app.mongo.db.GameOmok.find_one({"_id": ObjectId(room_id)})

        # 현재 턴과 플레이어 색상 일치 여부 확인
        if room["current_turn"] != player:
            return  # 턴이 아닌 플레이어의 돌 놓기 시도 무시

        # 돌을 놓을 위치가 이미 차 있는지 확인
        if room["board"][row][col] is not None:
            return  # 이미 돌이 놓인 곳에선 돌을 놓을 수 없음

        # 현재 턴을 변경
        next_turn = "black" if room["current_turn"] == "white" else "white"
        # next_turn = room["current_turn"]

        # 데이터베이스에 돌을 놓기
        board = room["board"]
        if board[row][col] is not None:
            return  # 이미 돌이 있는 곳이라면 돌을 놓지 않음

        # 해당 위치에 돌을 놓기
        board[row][col] = player
        app.mongo.db.GameOmok.update_one(
            {"_id": ObjectId(room_id)},
            {"$set": {"board": room["board"], "current_turn": next_turn}},
        )

        # 타이머 리셋 (60초로 초기화)
        game_timers[room_id] = 6

        # 게임 보드와 현재 턴 정보를 클라이언트에게 전달
        socketio.emit(
            "game_update",
            {
                "state": "진행중",
                "room_id": room_id,
                "row": row,
                "col": col,
                "player": player,
                "current_turn": next_turn,  # 클라이언트에게 현재 턴도 보내기
                # "board": rooms[room_id]["board"],
                "board": board,
                "time_left": game_timers[room_id],  # 타이머 상태도 클라이언트에 전달
            },
            room=room_id,
        )

        # 타이머를 1초씩 감소시켜서 클라이언트에 전송
        while game_timers[room_id] > 0:
            game_timers[room_id] -= 0.5  # 1초 감소
            socketio.emit(
                "game_update",
                {
                    "time_left": game_timers[room_id],  # 남은 시간
                    # "current_turn": next_turn,  # 현재 턴
                },
                room=room_id,
            )
            time.sleep(1)  # 1초마다 갱신

        # 타이머가 0이 되면 게임 종료 처리
        winner = next_turn  # 현재 턴의 플레이어를 승자로 설정
        loser = "black" if winner == "white" else "white"  # 반대 턴의 플레이어는 패자
        print(f"게임 종료: 승자 {winner}, 패자 {loser}")

        # 게임 종료를 위한 handle_timeout_game 호출
        socketio.emit(
            "game_update",
            {
                "time_left": 0,  # 타이머 종료
                "game_state": "게임 종료",
                "winner": winner,  # 승자
                "loser": loser,  # 패자
            },
            room=room_id,
        )

        # timeout_game 이벤트 처리
        socketio.emit(
            "timeout_game",
            {
                "room_id": room_id,
                "winner_id": winner,
                "loser_id": loser,
                "bet_amount": room["bet_amount"],  # 베팅 금액을 room에서 가져옴
            },
            room=room_id,
        )

        print(
            f"돌을 놓은 위치: ({row}, {col}), 플레이어: {player}, 현재 턴: {next_turn}"
        )  # 로그 추가
        print(
            f"game_update 이벤트 전송: {room_id}, {row}, {col}, {player}, {next_turn}"
        )

    # @socketio.on("room_created")
    # def handle_room_created(room_data):
    #     # 방이 생성된 후 모든 클라이언트에게 방 목록을 갱신합니다.
    #     print(f"새로운 방이 생성되었습니다: {room_data['room_name']}")
    #     rooms = app.mongo.db.GameOmok.find({"state": {"$in": ["대기중", "진행중"]}})
    #     rooms_list = []
    #     for room in rooms:
    #         room_data = {
    #             "room_name": room.get("room_name"),
    #             "state": room.get("state"),
    #             "_id": str(room.get("_id")),  # _id를 문자열로 변환
    #         }
    #         rooms_list.append(room_data)
    #     emit("update_rooms", rooms_list, broadcast=True)  # 모든 클라이언트에 방송

    # @socketio.on("disconnect")
    # def handle_disconnect():
    #     print("Client disconnected")

    # @socketio.on("disconnect")
    # def on_disconnect():
    #     leave_room(room_id)
    #     emit("status", {"message": "A player has disconnected."}, room=room_id)

    @socketio.on("end_game")
    def handle_end_game(data):
        room_id = data["room_id"]
        winner_id = data["winner_id"]
        loser_id = data["loser_id"]
        draw = data["draw"]
        bet_amount = data["bet_amount"]

        print("엔드게임 소켓 룸 아이디", room_id)

        # winner_id가 'black'이면 blackstone 값을 winner_id에 넣어줌
        if winner_id == "black":
            room = app.mongo.db.GameOmok.find_one({"_id": ObjectId(room_id)})
            winner_id = room["blackstone"]  # blackstone 값을 winner_id에 할당

        # winner_id가 'white'이면 whitestone 값을 winner_id에 넣어줌
        elif winner_id == "white":
            room = app.mongo.db.GameOmok.find_one({"_id": ObjectId(room_id)})
            winner_id = room["whitestone"]  # whitestone 값을 winner_id에 할당

        # loser_id가 'black'이면 blackstone 값을 loser_id에 넣어줌
        if loser_id == "black":
            room = app.mongo.db.GameOmok.find_one({"_id": ObjectId(room_id)})
            loser_id = room["blackstone"]  # blackstone 값을 loser_id에 할당

        # loser_id가 'white'이면 whitestone 값을 loser_id에 넣어줌
        elif loser_id == "white":
            room = app.mongo.db.GameOmok.find_one({"_id": ObjectId(room_id)})
            loser_id = room["whitestone"]  # whitestone 값을 loser_id에 할당

        # GameBlackjack 컬렉션에서 게임 종료 상태 업데이트
        app.mongo.db.GameOmok.update_one(
            {"_id": ObjectId(room_id)},
            {
                "$set": {
                    "state": "종료",
                    "winner": winner_id,
                    "loser": loser_id,
                    "draw": draw,
                    "end_time": datetime.now(pytz.utc) + timedelta(seconds=32400),
                }
            },
        )

        # 승자와 패자에게 리디렉션 명령을 보냄
        socketio.emit(
            "game_over",
            {"winner_id": str(winner_id), "loser_id": str(loser_id), "draw": draw},
            room=room_id,
        )

        # emit("game_ended", {"message": "게임이 종료되었습니다."}, room=room_id)

    @socketio.on("timeout_game")
    def handle_timeout_game(data):
        # global game_active_omok  # global로 게임 활성화 상태 추적

        # if not game_active_omok:
        #     return  # 이미 게임이 종료되었으면 더 이상 처리하지 않음
        room_id = data["room_id"]
        winner_id = data["winner_id"]
        loser_id = data["loser_id"]
        bet_amount = data["bet_amount"]

        print("아웃게임 소켓")
        print("아웃게임 소켓 winner_id", winner_id)
        print("아웃게임 소켓 loser_id", loser_id)
        print("아웃게임 소켓 bet_amount", bet_amount)

        if not winner_id or not loser_id:
            print("잘못된 게임 데이터 수신. 게임 종료 처리 실패.")
            return

        # GameBlackjack 컬렉션에서 게임 종료 상태 업데이트
        app.mongo.db.GameOmok.update_one(
            {"_id": ObjectId(room_id)},
            {
                "$set": {
                    "state": "종료",
                    "winner": ObjectId(winner_id),
                    "loser": ObjectId(loser_id),
                    "end_time": datetime.now(pytz.utc) + timedelta(seconds=32400),
                }
            },
        )

        # MongoDB Users 컬렉션에서 winner_id와 loser_id에 해당하는 사용자 찾기
        # winner의 current_points에 bet_amount 더하기
        app.mongo.db.Users.update_one(
            {"_id": ObjectId(winner_id)},
            {
                "$inc": {"current_points": int(bet_amount)}
            },  # current_points에 bet_amount를 더함
        )

        # loser의 current_points에 bet_amount 빼기
        app.mongo.db.Users.update_one(
            {"_id": ObjectId(loser_id)},
            {
                "$inc": {"current_points": -int(bet_amount)}
            },  # current_points에서 bet_amount를 뺌
        )

        # 승자와 패자에게 리디렉션 명령을 보냄
        socketio.emit(
            "game_over",
            {"winner_id": winner_id, "loser_id": loser_id},
            room=room_id,
        )

        # emit("game_ended", {"message": "게임이 종료되었습니다."}, room=room_id)
        # game_active_omok = False  # 게임 종료 상태로 설정
        print("게임 종료 처리 완료")
        
# if __name__ == '__main__':
#     # WebSocket 서버 실행
#     socketio.run(app, host="0.0.0.0", port=5000)  # 외부에서 접근 가능하도록 설정

if __name__ == '__main__':
    # port = int(os.environ.get("PORT", 5000))  # Railway에서 PORT 환경변수 사용
    port = int(os.getenv("PORT", 5000))  # Railway에서 PORT 환경 변수 가져오기
    socketio.run(app, host="0.0.0.0", port=port)  # 외부 접속 허용
