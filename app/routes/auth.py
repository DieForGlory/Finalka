# app/routes/auth.py
import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app.services import user_service
from app.extensions import db  # Импортируем db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Обрабатывает вход пользователя."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = user_service.get_user_by_username(username)

        if user and user.check_password(password):
            login_user(user, remember=remember)

            # --- ИЗМЕНЕНИЕ: Обновляем last_login ---
            try:
                user.last_login = datetime.datetime.now()
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Ошибка обновления last_login: {e}")
            # --- КОНЕЦ ИЗМЕНЕНИЯ ---

            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash("Неверное имя пользователя или пароль.", "error")

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Обрабатывает выход пользователя."""
    logout_user()
    return redirect(url_for('auth.login'))