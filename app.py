from flask import Flask, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room
import random
import math
import os

# Авто-определение папки, где лежит сам app.py
base_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    # Теперь он ищет index.html именно там, где лежит скрипт
    return send_from_directory(base_dir, 'index.html')

# Дальше весь твой остальной код (SERVERS, handle_join и т.д.) без изменений



# Настройки миров
SERVERS = {str(i): {"players": {}, "food": []} for i in range(1, 11)}
for s in SERVERS:
    SERVERS[s]['food'] = [{"id": j, "x": random.randint(-50, 50), "z": random.randint(-50, 50)} for j in range(30)]

# Обратный поиск: какой ID в какой комнате
player_to_room = {}

@socketio.on('join_server')
def handle_join(data):
    room = data.get('room', '1')
    name = data.get('name', f'Guest_{random.randint(100, 999)}')
    
    if room in SERVERS and len(SERVERS[room]['players']) < 10:
        join_room(room)
        player_to_room[request.sid] = room
        
        new_player = {
            "id": request.sid,
            "name": name,
            "x": random.randint(-10, 10),
            "z": random.randint(-10, 10),
            "length": 3,
            "color": random.randint(0, 0xffffff)
        }
        SERVERS[room]['players'][request.sid] = new_player
        
        emit('init', {"your_id": request.sid, "players": SERVERS[room]['players'], "food": SERVERS[room]['food']})
        emit('new_player', new_player, room=room, include_self=False)

@socketio.on('move')
def handle_move(data):
    room = player_to_room.get(request.sid)
    if not room: return
    
    player = SERVERS[room]['players'].get(request.sid)
    if not player: return

    # Обновляем координаты
    player['x'] = data['x']
    player['z'] = data['z']

    # ПРОВЕРКА ЕДЫ (теперь на сервере!)
    for f in SERVERS[room]['food'][:]:
        dist = math.sqrt((player['x'] - f['x'])**2 + (player['z'] - f['z'])**2)
        if dist < 1.8:
            player['length'] += 1
            SERVERS[room]['food'].remove(f)
            # Спавним новую еду
            new_f = {"id": random.randint(0, 999999), "x": random.randint(-50, 50), "z": random.randint(-50, 50)}
            SERVERS[room]['food'].append(new_f)
            emit('food_update', {"eaten": f['id'], "new": new_f}, room=room)

    emit('update', player, room=room, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    room = player_to_room.get(request.sid)
    if room and request.sid in SERVERS[room]['players']:
        del SERVERS[room]['players'][request.sid]
        del player_to_room[request.sid]
        emit('player_leave', request.sid, room=room)

import os

if __name__ == '__main__':
    # Render передает порт в переменной PORT
    port = int(os.environ.get('PORT', 5070))
    socketio.run(app, host='0.0.0.0', port=port)