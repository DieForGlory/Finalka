# run.py
import os
from app import create_app
from app.extensions import db  # <-- ИЗМЕНЕНИЕ: 'socketio' удален
from app.models import User, TaskLog

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'TaskLog': TaskLog}

if __name__ == '__main__':
    # --- ИЗМЕНЕНИЕ: ---
    # Запускаем стандартный сервер Flask, а не SocketIO
    # Убедитесь, что Redis запущен локально (docker run -d -p 6379:6379 redis:alpine),
    # иначе приложение запустится, но будет выдавать ошибки Redis.
    app.run(host='127.0.0.1', port=5004, debug=True)