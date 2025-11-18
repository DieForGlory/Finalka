# app/services/logging_service.py
import datetime
from app.extensions import db
from app.models import TaskLog


# Lock больше не нужен, DB управляет этим.

def load_logs():
    """Загружает все логи задач из DB."""
    # Загружаем логи, сортируя по дате (сначала новые)
    # .options(joinedload('owner')) - оптимизация, сразу грузит пользователя
    from sqlalchemy.orm import joinedload
    return TaskLog.query.options(joinedload(TaskLog.owner)).order_by(TaskLog.timestamp.desc()).all()


def log_task(task_id, owner_id, status, template_name):
    """
    Добавляет запись о завершенной задаче в лог DB.

    ВАЖНО: Эта функция должна вызываться ИЗНУТРИ
    Flask app_context(), так как она использует db.session.
    """

    new_log_entry = TaskLog(
        task_uuid=task_id,
        owner_id=owner_id,
        template_name=template_name,
        status=status,
        timestamp=datetime.datetime.now()
    )

    try:
        db.session.add(new_log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Мы не можем использовать current_app.logger, т.к. можем быть в потоке
        # без контекста. Просто выводим в stdout.
        print(f"[logging_service] Ошибка записи в DB: {e}")