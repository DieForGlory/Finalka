# app/config.py
import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key-that-you-should-change'

    # --- Base Directories ---
    APP_DIR = os.path.abspath(os.path.dirname(__file__))
    BASE_DIR = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    DATA_DIR = os.path.join(BASE_DIR, 'data')

    # --- НОВЫЙ ПУТЬ К БАЗЕ ДАННЫХ ---
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(DATA_DIR, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Отключаем ненужное отслеживание

    # --- ИЗМЕНЕНИЕ: ДОБАВЛЕН REDIS URL ---
    # Либо берем URL из docker-compose, либо (для локального запуска)
    # подключаемся к localhost.
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    # --- Folder Configurations (Based on DATA_DIR) ---
    UPLOAD_FOLDER = os.path.join(DATA_DIR, 'user_uploads')
    PROCESSED_FOLDER = os.path.join(DATA_DIR, 'processed_files')
    TEMPLATES_DB_FOLDER = os.path.join(DATA_DIR, 'template_definitions')
    TEMPLATE_EXCEL_FOLDER = os.path.join(DATA_DIR, 'template_excel_files')

    # --- Папки с данными (папка USERS_DATA_FOLDER больше не нужна) ---
    DICTIONARIES_FOLDER = os.path.join(DATA_DIR, 'dictionaries')
    GEOCODING_DATA_FOLDER = os.path.join(DATA_DIR, 'geocoding')

    # --- Data File Paths ---
    # USERS_FILE и TASK_LOG_FILE удалены, т.к. теперь они в 'app.db'
    COLUMN_DICTIONARY_FILE = os.path.join(DICTIONARIES_FOLDER, 'columns.json')
    VALUE_DICTIONARY_FILE = os.path.join(DICTIONARIES_FOLDER, 'values.json')
    ADDRESS_CSV_FILE = os.path.join(GEOCODING_DATA_FOLDER, 'addresses.csv')

    ALLOWED_EXTENSIONS = {'xlsx', 'xlsm'}