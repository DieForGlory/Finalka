# app/models.py
import uuid
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db


class User(UserMixin, db.Model):
    """
    Модель пользователя.
    UserMixin добавляет поля (is_authenticated, is_active, etc.)
    """
    __tablename__ = 'user'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user', index=True)  # 'user' or 'admin'

    # --- НОВОЕ ПОЛЕ ---
    last_login = db.Column(db.DateTime, nullable=True)
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    # Связь: "Какие логи задач принадлежат этому пользователю?"
    task_logs = db.relationship('TaskLog', back_populates='owner', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class TaskLog(db.Model):
    """
    Модель для логгирования каждой задачи парсинга.
    """
    __tablename__ = 'task_log'

    id = db.Column(db.Integer, primary_key=True)
    task_uuid = db.Column(db.String(36), index=True)  # task_id из task_statuses
    template_name = db.Column(db.String(255))
    status = db.Column(db.String(500))  # 'Готово!' или 'Ошибка: ...'
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.now)
    owner_id = db.Column(db.String(36), db.ForeignKey('user.id'))

    # Связь: "Какая задача принадлежит какому пользователю?"
    owner = db.relationship('User', back_populates='task_logs')