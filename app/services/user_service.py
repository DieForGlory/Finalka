# app/services/user_service.py
from app.extensions import db
from app.models import User  # <-- Импортируем нашу новую модель


# Класс User теперь живет в models.py, удаляем его отсюда

def get_user_by_id(user_id):
    """Находит пользователя по ID (UUID)."""
    return db.session.get(User, user_id)


def get_user_by_username(username):
    """Находит пользователя по username."""
    return User.query.filter_by(username=username).first()


def get_all_users():
    """Возвращает список всех объектов User."""
    return User.query.order_by(User.username).all()


def create_user(username, password, role='user'):
    """Создает нового пользователя в DB."""
    if not username or not password:
        raise ValueError("Имя пользователя и пароль не могут быть пустыми.")
    if get_user_by_username(username):
        raise ValueError("Пользователь с таким именем уже существует.")

    new_user = User(username=username, role=role)
    new_user.set_password(password)  # Хэшируем пароль

    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Ошибка при добавлении в DB: {e}")

    return new_user


def delete_user(user_id):
    """Удаляет пользователя из DB."""
    user = db.session.get(User, user_id)
    if user:
        try:
            # Нужно обработать связанные логи задач (иначе DB не даст удалить)
            # Вариант 1: Удалить все логи (каскадом)
            # (Настроили бы в models.py: cascade="all, delete-orphan")
            # Вариант 2: Отвязать (сейчас они просто отвяжутся, т.к. owner_id станет NULL)

            db.session.delete(user)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Ошибка удаления пользователя: {e}")
            return False
    return False