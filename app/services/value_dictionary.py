# app/services/value_dictionary.py
import json
import os
from flask import current_app

def _get_dictionary_path():
    """Получает путь к файлу из конфигурации приложения."""
    return current_app.config['VALUE_DICTIONARY_FILE']

def load_dictionary():
    """Загружает словарь правил из JSON-файла."""
    path = _get_dictionary_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_dictionary(data):
    """Сохраняет словарь правил в JSON-файл."""
    path = _get_dictionary_path()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        current_app.logger.error(f"Ошибка сохранения словаря {path}: {e}")

def add_entry(canonical_word, find_words_str):
    """Добавляет или обновляет правило в словаре."""
    dictionary = load_dictionary()
    find_words = [s.strip() for s in find_words_str.split('@1!') if s.strip()]
    dictionary[canonical_word] = find_words
    save_dictionary(dictionary)

def delete_entry(canonical_word):
    """Удаляет запись по каноничному слову."""
    dictionary = load_dictionary()
    if canonical_word in dictionary:
        del dictionary[canonical_word]
        save_dictionary(dictionary)

def get_reverse_lookup_map():
    """
    Создает 'обратный' словарь для быстрой замены вида {'слово_найти': 'слово_заменить'}.
    """
    dictionary = load_dictionary()
    reverse_map = {}
    for canonical_word, find_words_list in dictionary.items():
        for find_word in find_words_list:
            if find_word:
                reverse_map[find_word] = canonical_word
    return reverse_map