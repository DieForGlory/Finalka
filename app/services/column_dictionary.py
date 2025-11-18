# app/services/column_dictionary.py
import json
import os
import re
from flask import current_app

def _get_dictionary_path():
    """Получает путь к файлу из конфигурации приложения."""
    return current_app.config['COLUMN_DICTIONARY_FILE']

def load_dictionary():
    """
    Загружает словарь из JSON-файла.
    Если файл не найден или содержит ошибку, возвращает пустой словарь.
    """
    path = _get_dictionary_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_dictionary(data):
    """Сохраняет данные словаря в JSON-файл с красивым форматированием."""
    path = _get_dictionary_path()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        current_app.logger.error(f"Ошибка сохранения словаря {path}: {e}")

def get_reverse_dictionary(data=None):
    """
    Создает "обратный" словарь для быстрого поиска: {синоним: каноничное_имя}.
    Все ключи (синонимы) приводятся к нормализованному виду.
    """
    if data is None:
        data = load_dictionary()

    reverse_map = {}
    for canonical_name, synonyms in data.items():
        # Добавляем и само каноничное имя в список вариантов
        all_variants = synonyms + [canonical_name]
        for variant in all_variants:
            normalized_variant = _normalize(variant)
            reverse_map[normalized_variant] = canonical_name
    return reverse_map

def add_entry(canonical_name, synonyms_str):
    """Добавляет или обновляет запись в словаре."""
    dictionary = load_dictionary()
    synonyms = [s.strip() for s in synonyms_str.split('@1!') if s.strip()]
    dictionary[canonical_name] = synonyms
    save_dictionary(dictionary)

def delete_entry(canonical_name):
    """Удаляет запись (каноничное имя и все его синонимы) из словаря."""
    dictionary = load_dictionary()
    if canonical_name in dictionary:
        del dictionary[canonical_name]
        save_dictionary(dictionary)

def _normalize(text):
    """
    Внутренняя функция для приведения текста к единому виду.
    """
    if not isinstance(text, str):
        text = str(text)
    return re.sub(r'[\s\W_]+', '', text.lower())