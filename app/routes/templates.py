# app/routes/templates.py
import os
import glob
import json
import uuid
from flask import (Blueprint, render_template, request, flash, redirect,
                   url_for, current_app, send_from_directory)
from werkzeug.utils import secure_filename
from app.utils.helpers import allowed_file
from flask_login import login_required, current_user

templates_bp = Blueprint('templates', __name__, url_prefix='/templates')


def _check_template_access(template_id):
    """
    Вспомогательная функция для проверки доступа к шаблону.
    Возвращает (template_data, has_access)
    """
    json_path = os.path.join(current_app.config['TEMPLATES_DB_FOLDER'], f"{secure_filename(template_id)}.json")
    if not os.path.exists(json_path):
        return None, False  # Шаблон не найден

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
    except Exception as e:
        current_app.logger.error(f"Ошибка чтения файла шаблона {template_id}: {e}")
        return None, False  # Ошибка чтения файла

    owner_id = template_data.get('owner_id')

    # Доступ разрешен, если:
    # 1. Пользователь - админ
    # 2. Шаблон публичный (owner_id == None)
    # 3. Пользователь - владелец
    if current_user.role == 'admin' or owner_id is None or owner_id == current_user.id:
        return template_data, True  # Доступ разрешен

    return template_data, False  # Доступ запрещен


@templates_bp.route('/')
@login_required
def list():
    """Отображает список шаблонов, доступных пользователю."""
    template_files = glob.glob(os.path.join(current_app.config['TEMPLATES_DB_FOLDER'], '*.json'))
    templates_data = []

    for f in template_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                data['id'] = os.path.basename(f).replace('.json', '')

                owner_id = data.get('owner_id')
                is_admin = current_user.role == 'admin'
                is_owner = (owner_id == current_user.id)
                is_public = (owner_id is None)  # Шаблон без владельца = public

                # Показываем, если: админ, ИЛИ владелец, ИЛИ шаблон публичный
                if is_admin or is_owner or is_public:
                    templates_data.append(data)
        except Exception as e:
            current_app.logger.error(f"Ошибка чтения шаблона {f}: {e}")

    # Сортировка для админа: сначала свои, потом остальные
    if current_user.role == 'admin':
        templates_data.sort(key=lambda x: (x.get('owner_id') != current_user.id, x.get('template_name', '')))

    return render_template('templates_list.html', templates=templates_data)


@templates_bp.route('/new')
@login_required
def new():
    """Страница создания нового шаблона."""
    return render_template('create_template.html')


def _gather_rules_from_form(request_form):
    """
    Вспомогательная функция для сбора ВСЕХ типов правил из POST-формы
    (используется в create и edit).
    """

    rules_data = {}

    # 1. Правила для столбцов (Колонка -> Колонка)
    rules_data['rules'] = []
    source_cols = request_form.getlist('source_col')  # ИСПРАВЛЕНО
    template_cols = request_form.getlist('template_col')
    source_sheets = request_form.getlist('source_sheet')
    manual_rule_names = request_form.getlist('manual_rule_name')  # НОВОЕ

    for i in range(len(source_cols)):
        if source_cols[i] and template_cols[i]:
            sheet_name = source_sheets[i] if i < len(source_sheets) and source_sheets[i] else 'Лист1'
            rules_data['rules'].append({
                "source_sheet": sheet_name,
                "source_col": source_cols[i].upper(),  # ИСПРАВЛЕНО
                "template_col": template_cols[i].upper(),
                "name": manual_rule_names[i] if i < len(manual_rule_names) and manual_rule_names[i] else ""  # НОВОЕ
            })

    # 2. Правила для ячеек (Ячейка -> Ячейка)
    rules_data['cell_mappings'] = []
    source_sheet_cells = request_form.getlist('source_sheet_cell')
    source_cell_cells = request_form.getlist('source_cell_cell')
    dest_cell_cells = request_form.getlist('dest_cell_cell')
    cell_mapping_names = request_form.getlist('cell_mapping_name')  # НОВОЕ

    for i in range(len(source_cell_cells)):
        if source_cell_cells[i] and dest_cell_cells[i]:
            sheet_name = source_sheet_cells[i] if i < len(source_sheet_cells) and source_sheet_cells[i] else 'Лист1'
            rules_data['cell_mappings'].append({
                "source_sheet": sheet_name,
                "source_cell": source_cell_cells[i].upper(),
                "dest_cell": dest_cell_cells[i].upper(),
                "name": cell_mapping_names[i] if i < len(cell_mapping_names) and cell_mapping_names[i] else ""  # НОВОЕ
            })

    # 3. Правила для формул (Row-by-row)
    rules_data['formula_rules'] = []
    source_sheets_formula = request_form.getlist('source_sheet_formula')
    target_sheets_formula = request_form.getlist('target_sheet_formula')
    target_cols_formula = request_form.getlist('target_col_formula')
    formula_strings = request_form.getlist('formula_string')
    formula_rule_names = request_form.getlist('formula_rule_name')  # НОВОЕ

    for i in range(len(target_cols_formula)):
        if target_cols_formula[i] and formula_strings[i]:
            source_sheet = source_sheets_formula[i] if i < len(source_sheets_formula) and source_sheets_formula[
                i] else 'Лист1'
            target_sheet = target_sheets_formula[i] if i < len(target_sheets_formula) and target_sheets_formula[
                i] else 'Лист1'
            rules_data['formula_rules'].append({
                "source_sheet": source_sheet,
                "target_sheet": target_sheet,
                "target_col": target_cols_formula[i].upper(),
                "formula": formula_strings[i],
                "name": formula_rule_names[i] if i < len(formula_rule_names) and formula_rule_names[i] else ""  # НОВОЕ
            })

    # 4. Правила для статичных значений (Fill column)
    rules_data['static_value_rules'] = []
    target_sheets_static = request_form.getlist('target_sheet_static')
    target_cols_static = request_form.getlist('target_col_static')
    static_values = request_form.getlist('static_value')
    static_value_rule_names = request_form.getlist('static_value_rule_name')  # НОВОЕ

    for i in range(len(target_cols_static)):
        if target_cols_static[i] and static_values[i]:
            sheet_name = target_sheets_static[i] if i < len(target_sheets_static) and target_sheets_static[
                i] else 'Лист1'
            rules_data['static_value_rules'].append({
                "target_sheet": sheet_name,
                "target_col": target_cols_static[i].upper(),
                "value": static_values[i],
                "name": static_value_rule_names[i] if i < len(static_value_rule_names) and static_value_rule_names[
                    i] else ""  # НОВОЕ
            })

    # 5. Настройки листов (Sheet Settings)
    rules_data['sheet_settings'] = []
    setting_sheet_names = request_form.getlist('setting_sheet_name')
    setting_start_cells = request_form.getlist('setting_start_cell')
    for i in range(len(setting_sheet_names)):
        if setting_sheet_names[i] and setting_start_cells[i]:
            rules_data['sheet_settings'].append({
                "sheet_name": setting_sheet_names[i],
                "start_cell": setting_start_cells[i].upper()
            })

    # 6. Правила заполнения из ячейки (Cell-to-Column Fill)
    rules_data['source_cell_fill_rules'] = []
    source_sheets_fill = request_form.getlist('source_sheet_fill')
    source_cells_fill = request_form.getlist('source_cell_fill')
    target_sheets_fill = request_form.getlist('target_sheet_fill')
    target_cols_fill = request_form.getlist('target_col_fill')
    source_cell_fill_rule_names = request_form.getlist('source_cell_fill_rule_name')  # НОВОЕ

    for i in range(len(source_cells_fill)):
        if source_cells_fill[i] and target_cols_fill[i]:
            source_sheet = source_sheets_fill[i] if i < len(source_sheets_fill) and source_sheets_fill[i] else 'Лист1'
            target_sheet = target_sheets_fill[i] if i < len(target_sheets_fill) and target_sheets_fill[i] else 'Лист1'
            rules_data['source_cell_fill_rules'].append({
                "source_sheet": source_sheet,
                "source_cell": source_cells_fill[i].upper(),
                "target_sheet": target_sheet,
                "target_col": target_cols_fill[i].upper(),
                "name": source_cell_fill_rule_names[i] if i < len(source_cell_fill_rule_names) and
                                                          source_cell_fill_rule_names[i] else ""  # НОВОЕ
            })

    return rules_data


@templates_bp.route('/create', methods=['POST'])
@login_required
def create():
    """Обрабатывает создание нового шаблона."""
    try:
        template_name = request.form.get('template_name')
        header_start_cell = request.form.get('header_start_cell').upper()
        excel_file = request.files.get('excel_file')

        if not (template_name and excel_file and excel_file.filename):
            flash("Ошибка: Название шаблона и Excel-файл должны быть заполнены.", "error")
            return redirect(url_for('templates.new'))

        if not allowed_file(excel_file.filename):
            flash("Ошибка: Недопустимый формат файла Excel.", "error")
            return redirect(url_for('templates.new'))

        template_id = str(uuid.uuid4())
        _, file_extension = os.path.splitext(excel_file.filename)
        saved_excel_filename = f"{template_id}{file_extension}"
        excel_file.save(os.path.join(current_app.config['TEMPLATE_EXCEL_FOLDER'], saved_excel_filename))

        # --- Сбор всех правил ---
        rules_data = _gather_rules_from_form(request.form)

        # --- Определение Владельца ---
        if current_user.role == 'admin':
            new_owner_id = None  # Админ создает публичный шаблон
        else:
            new_owner_id = current_user.id  # Пользователь создает приватный шаблон

        # --- Создание объекта JSON шаблона ---
        template_data = {
            "template_name": template_name,
            "excel_file": saved_excel_filename,
            "original_filename": excel_file.filename,
            "post_function": request.form.get('post_function', 'none'),
            "visible_rows_only": 'visible_rows_only' in request.form,
            "header_start_cell": header_start_cell,
            "owner_id": new_owner_id,

            # Добавляем все 6 типов правил
            **rules_data
        }

        # Сохраняем JSON-файл
        with open(os.path.join(current_app.config['TEMPLATES_DB_FOLDER'], f"{template_id}.json"), 'w',
                  encoding='utf-8') as f:
            json.dump(template_data, f, ensure_ascii=False, indent=4)

        flash(f"Шаблон '{template_name}' успешно создан!", "success")
        return redirect(url_for('templates.list'))

    except Exception as e:
        flash(f"Произошла ошибка при создании шаблона: {e}", "error")
        current_app.logger.error(f"Ошибка при создании шаблона: {e}", exc_info=True)
        return redirect(url_for('templates.new'))


@templates_bp.route('/edit/<template_id>', methods=['GET', 'POST'])
@login_required
def edit(template_id):
    """Страница редактирования шаблона."""
    template_data, has_access = _check_template_access(template_id)

    if template_data is None:
        flash("Шаблон не найден.", "error")
        return redirect(url_for('templates.list'))
    if not has_access:
        flash("У вас нет доступа к редактированию этого шаблона.", "error")
        return redirect(url_for('templates.list'))

    json_path = os.path.join(current_app.config['TEMPLATES_DB_FOLDER'], f"{secure_filename(template_id)}.json")

    if request.method == 'POST':
        try:
            # --- Обновление основных данных и настроек ---
            template_data['template_name'] = request.form.get('template_name')
            template_data['header_start_cell'] = request.form.get('header_start_cell').upper()
            template_data['post_function'] = request.form.get('post_function', 'none')
            template_data['visible_rows_only'] = 'visible_rows_only' in request.form

            # --- Обновление файла шаблона (если загружен новый) ---
            new_excel_file = request.files.get('excel_file')
            if new_excel_file and new_excel_file.filename:
                if allowed_file(new_excel_file.filename):
                    old_excel_path = os.path.join(current_app.config['TEMPLATE_EXCEL_FOLDER'],
                                                  template_data.get('excel_file', ''))
                    if os.path.exists(old_excel_path):
                        os.remove(old_excel_path)

                    _, file_extension = os.path.splitext(new_excel_file.filename)
                    saved_excel_filename = f"{template_id}{file_extension}"
                    new_excel_file.save(os.path.join(current_app.config['TEMPLATE_EXCEL_FOLDER'], saved_excel_filename))
                    template_data['excel_file'] = saved_excel_filename
                    template_data['original_filename'] = new_excel_file.filename
                else:
                    flash("Недопустимый формат файла.", "error")
                    return redirect(url_for('templates.edit', template_id=template_id))

            # --- Сбор всех типов правил ---
            rules_data = _gather_rules_from_form(request.form)
            # Обновляем словарь template_data новыми правилами
            template_data.update(rules_data)

            # Владелец (owner_id) при редактировании НЕ МЕНЯЕТСЯ.
            # Он устанавливается один раз при создании.

            # Сохраняем обновленный JSON
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=4)
            flash("Шаблон успешно обновлен!", "success")

            # --- ИЗМЕНЕНИЕ: "Сохранить и остаться" ---
            return redirect(url_for('templates.edit', template_id=template_id))

        except Exception as e:
            flash(f"Ошибка при обновлении: {e}", "error")
            current_app.logger.error(f"Ошибка при обновлении шаблона {template_id}: {e}", exc_info=True)
            return redirect(url_for('templates.edit', template_id=template_id))

    # Блок GET-запроса (просто отображаем страницу)
    return render_template('edit_template.html', template=template_data, template_id=template_id)


@templates_bp.route('/download/<template_id>')
@login_required
def download(template_id):
    """Отдает Excel-файл шаблона для скачивания."""
    template_data, has_access = _check_template_access(template_id)

    if template_data is None:
        flash("Шаблон не найден.", "error")
        return redirect(url_for('templates.list'))
    if not has_access:
        flash("У вас нет доступа к этому шаблону.", "error")
        return redirect(url_for('templates.list'))

    excel_filename = template_data.get('excel_file')
    original_filename = template_data.get('original_filename', 'template.xlsx')

    if not excel_filename or not os.path.exists(
            os.path.join(current_app.config['TEMPLATE_EXCEL_FOLDER'], excel_filename)):
        flash("Файл Excel для этого шаблона не найден.", "error")
        return redirect(url_for('templates.edit', template_id=template_id))

    return send_from_directory(current_app.config['TEMPLATE_EXCEL_FOLDER'], excel_filename, as_attachment=True,
                               download_name=original_filename)


@templates_bp.route('/delete/<template_id>', methods=['POST'])
@login_required
def delete(template_id):
    """Удаляет шаблон (JSON и связанный Excel-файл)."""
    template_data, has_access = _check_template_access(template_id)

    if template_data is None:
        flash("Шаблон не найден.", "error")
        return redirect(url_for('templates.list'))
    if not has_access:
        flash("У вас нет доступа к удалению этого шаблона.", "error")
        return redirect(url_for('templates.list'))

    try:
        json_path = os.path.join(current_app.config['TEMPLATES_DB_FOLDER'], f"{secure_filename(template_id)}.json")

        # Удаляем Excel-файл
        excel_filename = template_data.get('excel_file')
        if excel_filename:
            excel_path = os.path.join(current_app.config['TEMPLATE_EXCEL_FOLDER'], excel_filename)
            if os.path.exists(excel_path):
                os.remove(excel_path)

        # Удаляем JSON-файл
        os.remove(json_path)
        flash("Шаблон успешно удален.", "success")

    except Exception as e:
        flash(f"Ошибка при удалении: {e}", "error")
        current_app.logger.error(f"Ошибка при удалении шаблона {template_id}: {e}", exc_info=True)

    return redirect(url_for('templates.list'))