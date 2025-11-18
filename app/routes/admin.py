# app/routes/admin.py
import os
from flask import (Blueprint, render_template, request,
                   current_app, flash, redirect, url_for)
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.utils.decorators import admin_required
from app.services import user_service, logging_service
from app.models import User, TaskLog  # Import models for report

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Главная страница админ-панели."""
    return redirect(url_for('admin.reports'))


@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    """Отчет по активности пользователей."""

    # --- ИЗМЕНЕНИЕ: Загружаем пользователей и логи из DB ---
    all_users = user_service.get_all_users()
    all_logs = logging_service.load_logs()

    report_data = {}

    # 1. Инициализируем всех пользователей
    for user in all_users:
        report_data[user.id] = {
            'username': user.username,
            'tasks_run': 0,
            'tasks_success': 0,
            'tasks_error': 0,
            'task_log': []
        }

    # 2. Распределяем логи по пользователям
    for log in all_logs:
        if log.owner_id in report_data:
            user_data = report_data[log.owner_id]
            user_data['tasks_run'] += 1

            if 'Ошибка' in log.status:
                user_data['tasks_error'] += 1
            else:
                user_data['tasks_success'] += 1

            user_data['task_log'].append(log)
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    return render_template('admin_reports.html', report_data=report_data)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """Управление пользователями."""
    all_users = user_service.get_all_users()
    return render_template('admin_users.html', users=all_users)


@admin_bp.route('/users/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    """Добавление нового пользователя."""
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'user')

    if not username or not password:
        flash("Имя пользователя и пароль обязательны.", "error")
        return redirect(url_for('admin.users'))

    if user_service.get_user_by_username(username):
        flash(f"Пользователь с именем '{username}' уже существует.", "error")
        return redirect(url_for('admin.users'))

    user_service.create_user(username, password, role)
    flash(f"Пользователь '{username}' успешно создан.", "success")
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/delete/<string:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Удаление пользователя."""
    user = user_service.get_user_by_id(user_id)
    if user:
        if user.role == 'admin':
            flash("Нельзя удалить администратора.", "error")
        else:
            user_service.delete_user(user_id)
            flash(f"Пользователь '{user.username}' удален.", "success")
    else:
        flash("Пользователь не найден.", "error")
    return redirect(url_for('admin.users'))


@admin_bp.route('/geocoding', methods=['GET', 'POST'])
@login_required
@admin_required
def geocoding_ui():
    """Страница управления файлом геокодинга."""
    if request.method == 'POST':
        if 'address_file' not in request.files:
            flash('Файл не найден в запросе.', 'error')
            return redirect(request.url)

        file = request.files['address_file']
        if file.filename == '':
            flash('Файл не выбран.', 'error')
            return redirect(request.url)

        if file and file.filename.endswith('.csv'):
            try:
                filename = 'addresses.csv'
                save_path = os.path.join(current_app.config['GEOCODING_DATA_FOLDER'], filename)

                # (Пере)записываем файл
                file.save(save_path)

                # --- Перезагружаем сервис геокодинга ---
                # (Это предполагает, что ваш geocoding_service имеет функцию reload)
                from app.services import geocoding_service
                geocoding_service.load_addresses(force=True)
                # ---

                flash('База геокодинга успешно обновлена.', 'success')
            except Exception as e:
                flash(f'Ошибка при сохранении файла: {e}', 'error')

            return redirect(url_for('admin.geocoding_ui'))
        else:
            flash('Разрешены только файлы .csv', 'error')

    return render_template('admin_geocoding.html')