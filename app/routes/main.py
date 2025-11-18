# app/routes/main.py
import os
import io
import uuid
import json
from flask import (Blueprint, render_template, request, jsonify,
                   send_from_directory, current_app, send_file)
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user

from app.services.excel_processor import process_excel_hybrid
# ИЗМЕНЕНИЕ: импортируем redis_client, удаляем task_statuses
from app.extensions import executor, redis_client

main_bp = Blueprint('main', __name__)

# Константа времени жизни ключа в Redis (например, 24 часа)
TASK_EXPIRY_TIME_SECONDS = 86400


@main_bp.route('/api/task_status/<string:task_id>')
def get_task_status(task_id):
    """
    Отдает клиенту статус задачи из Redis.
    """
    if not redis_client:
        return jsonify({'status': 'Ошибка: Сервис Redis не доступен.'}), 503

    status_json = redis_client.get(task_id)

    if not status_json:
        return jsonify({'status': 'NOT_FOUND'}), 404

    status_info = json.loads(status_json)

    # Проверка прав доступа
    if status_info.get('owner_id') != current_user.id and current_user.role != 'admin':
        return jsonify({'status': 'FORBIDDEN'}), 403

    # ИЗМЕНЕНИЕ: Файл 'result_file' больше не хранится в статусе.
    # Флаг 'result_ready' теперь зависит от статуса.
    status_info['result_ready'] = status_info.get('status') == 'Готово!'

    return jsonify(status_info)


@main_bp.route('/')
@login_required
def index():
    """Главная страница, отображает список доступных шаблонов."""
    templates_path = current_app.config['TEMPLATES_DB_FOLDER']
    templates = []

    if os.path.isdir(templates_path):
        for f_name in os.listdir(templates_path):
            if f_name.endswith('.json'):
                try:
                    with open(os.path.join(templates_path, f_name), 'r', encoding='utf-8') as f:
                        data = json.load(f)

                        owner_id = data.get('owner_id')
                        is_admin = current_user.role == 'admin'
                        is_owner = (owner_id == current_user.id)
                        is_public = (owner_id is None)

                        if is_admin or is_owner or is_public:
                            templates.append({
                                'id': f_name.replace('.json', ''),
                                'name': data.get('template_name', 'Без имени'),
                                'owner_id': owner_id
                            })
                except Exception as e:
                    current_app.logger.error(f"Ошибка чтения шаблона {f_name}: {e}")

    if current_user.role == 'admin':
        templates.sort(key=lambda x: (x.get('owner_id') != current_user.id, x['name']))

    return render_template('index.html', templates=templates)


@main_bp.route('/process', methods=['POST'])
@login_required
def process_files():
    """Запускает фоновую задачу обработки Excel."""
    if not redis_client:
        return jsonify({'error': 'Ошибка: Сервис Redis не доступен.'}), 503

    if 'source_file' not in request.files:
        return jsonify({'error': 'Не найден файл-источник.'})

    source_file = request.files['source_file']
    if source_file.filename == '':
        return jsonify({'error': 'Файл-источник не выбран.'})

    source_file_in_memory = io.BytesIO(source_file.read())
    template_file_in_memory = None

    saved_template_id = request.form.get('saved_template')

    # Инициализация всех переменных
    template_rules, cell_mappings, formula_rules, static_value_rules, sheet_settings = [], [], [], [], []
    source_cell_fill_rules = []
    original_template_filename = "template.xlsx"
    start_row = 1
    post_function = 'none'
    visible_rows_only = False

    try:
        if saved_template_id:
            # --- ИСПОЛЬЗУЕМ СОХРАНЕННЫЙ ШАБЛОН ---
            json_path = os.path.join(current_app.config['TEMPLATES_DB_FOLDER'],
                                     f"{secure_filename(saved_template_id)}.json")

            if not os.path.exists(json_path):
                return jsonify({'error': 'Файл шаблона не найден.'})

            with open(json_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)

            # --- ПРОВЕРКА ДОСТУПА К ШАБЛОНУ ---
            owner_id = template_data.get('owner_id')
            if owner_id is not None:
                if current_user.role != 'admin' and owner_id != current_user.id:
                    current_app.logger.warning(
                        f"Пользователь {current_user.id} пытался использовать чужой шаблон {saved_template_id}")
                    return jsonify({'error': 'Доступ к этому шаблону запрещен.'})

            excel_folder = current_app.config['TEMPLATE_EXCEL_FOLDER']
            template_filename = template_data.get('excel_file')
            original_template_filename = template_data.get('original_filename', template_filename)
            template_file_path = os.path.join(excel_folder, template_filename)

            with open(template_file_path, 'rb') as tf:
                template_file_in_memory = io.BytesIO(tf.read())

            header_start_cell = template_data.get('header_start_cell', 'A1')
            if header_start_cell:
                start_row_match = "".join(filter(str.isdigit, header_start_cell))
                if start_row_match:
                    start_row = int(start_row_match)

            # --- СБОР ВСЕХ ПРАВИЛ ---
            template_rules = template_data.get('rules', [])
            cell_mappings = template_data.get('cell_mappings', [])
            formula_rules = template_data.get('formula_rules', [])
            static_value_rules = template_data.get('static_value_rules', [])
            sheet_settings = template_data.get('sheet_settings', [])
            post_function = template_data.get('post_function', 'none')
            visible_rows_only = template_data.get('visible_rows_only', False)
            source_cell_fill_rules = template_data.get('source_cell_fill_rules', [])

        else:
            # --- РУЧНАЯ НАСТРОЙКА ---
            if 'template_file' not in request.files:
                return jsonify({'error': 'Файл-шаблон для ручной настройки не загружен.'})
            template_file = request.files['template_file']
            template_file_in_memory = io.BytesIO(template_file.read())
            original_template_filename = template_file.filename

            template_range_start_str = request.form.get('template_range_start', 'A1')
            if template_range_start_str:
                start_row_match = "".join(filter(str.isdigit, template_range_start_str))
                if start_row_match:
                    start_row = int(start_row_match)

        ranges_settings = {'t_start_row': start_row}
        task_id = str(uuid.uuid4())

        # --- ИЗМЕНЕНИЕ: Сохраняем начальный статус в Redis ---
        print(f"--- DEBUG [main.py]: Задача {task_id} создана ---")

        initial_data = {
            'status': 'Задача поставлена в очередь...',
            'progress': 0,
            'owner_id': current_user.id,
            'warnings': []
            # 'template_filename' будет добавлен в конце
        }

        redis_client.setex(
            task_id,
            TASK_EXPIRY_TIME_SECONDS,
            json.dumps(initial_data)
        )
        # --- КОНЕЦ ИЗМЕНЕНИЯ ---

        print(f"--- DEBUG [main.py]: Вызываю executor.submit для {task_id} ---")

        executor.submit(
            process_excel_hybrid,
            # ВАЖНО: 'task_statuses' больше не передается как аргумент
            task_id,
            source_file_in_memory,
            template_file_in_memory,
            ranges_settings,
            sheet_settings,
            template_rules,
            post_function,
            original_template_filename,
            # task_statuses, <-- УДАЛЕНО
            cell_mappings,
            formula_rules,
            static_value_rules,
            visible_rows_only,
            source_cell_fill_rules
        )

        print(f"--- DEBUG [main.py]: executor.submit для {task_id} ВЫЗВАН (HTTP 200 будет отправлен) ---")

        return jsonify({'task_id': task_id})

    except Exception as e:
        # --- DEBUG PRINT 4 ---
        print(f"--- DEBUG [main.py]: КРИТИЧЕСКАЯ ОШИБКА в process_files: {e} ---")
        current_app.logger.critical(f"Критическая ошибка в process_files: {e}", exc_info=True)
        return jsonify({'error': f'Произошла внутренняя ошибка: {e}'})


@main_bp.route('/status/<task_id>')
@login_required
def task_status(task_id):
    """
    (Fallback) Возвращает статус задачи.
    Перенаправляем логику на новый /api/task_status/
    """
    # Просто вызываем другую view-функцию
    return get_task_status(task_id)


@main_bp.route('/download/<task_id>')
@login_required
def download_file(task_id):
    """Отдает готовый файл для скачивания (теперь с диска)."""
    if not redis_client:
        return "Ошибка: Сервис Redis не доступен.", 503

    # --- ИЗМЕНЕНИЕ: Получаем статус из Redis ---
    status_json = redis_client.get(task_id)
    if not status_json:
        return "Задача не найдена.", 404

    task = json.loads(status_json)
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    # Проверка прав
    if task.get('owner_id') != current_user.id and current_user.role != 'admin':
        current_app.logger.warning(f"Пользователь {current_user.id} пытался скачать чужой файл {task_id}")
        return "Доступ к файлу запрещен.", 403

    # Проверка готовности файла
    if task.get('status') != 'Готово!':
        return "Файл не найден или еще не готов.", 404

    # --- ИЗМЕНЕНИЕ: Отдаем файл с диска ---

    # Имя файла, под которым он сохранен в /data/processed_files
    # Имя файла = ID задачи + расширение.
    # Убедитесь, что excel_processor сохраняет как .xlsx
    saved_filename = f"{task_id}.xlsx"

    # Имя, которое увидит пользователь при скачивании
    template_filename = task.get('template_filename', 'template.xlsx')
    download_name = f"processed_{task_id[:8]}_{template_filename}"

    processed_folder = current_app.config['PROCESSED_FOLDER']

    print(f"--- DEBUG [main.py]: Отдаю файл: {os.path.join(processed_folder, saved_filename)} как {download_name} ---")

    # send_from_directory - это безопасный способ отдать файл из папки
    return send_from_directory(
        processed_folder,
        saved_filename,
        as_attachment=True,
        download_name=download_name,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---