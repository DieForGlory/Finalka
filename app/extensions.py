# app/extensions.py
import redis
from .config import Config # <-- Важно: импортируем Config
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_executor import Executor

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Пожалуйста, войдите, чтобы получить доступ к этой странице."
login_manager.login_message_category = "error"

db = SQLAlchemy()
migrate = Migrate()
executor = Executor()

# --- ИЗМЕНЕНИЕ ---
# task_statuses = {} # <-- УДАЛЕНО

# Добавляем клиент Redis.
# Он будет использовать REDIS_URL из Config.
# decode_responses=True автоматически конвертирует ответы из bytes в str.
try:
    redis_client = redis.from_url(Config.REDIS_URL, decode_responses=True)
    redis_client.ping()
    print("--- Успешное подключение к Redis ---")
except Exception as e:
    print(f"--- ОШИБКА ПОДКЛЮЧЕНИЯ K REDIS: {e} ---")
    print("--- Убедитесь, что Redis запущен. Фоновые задачи не будут работать. ---")
    redis_client = None
# --- КОНЕЦ ИЗМЕНЕНИЯ ---