# app/utils/decorators.py
from functools import wraps
from flask import abort
from flask_login import current_user

def admin_required(f):
    """
    Декоратор, ограничивающий доступ только для пользователей с ролью 'admin'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403) # Доступ запрещен
        return f(*args, **kwargs)
    return decorated_function