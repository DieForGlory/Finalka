import json
import os

VALUE_DICT_FILE = 'value_dictionary.json'


def load_dictionary():
    """Загружает словарь правил из JSON-файла."""
    if not os.path.exists(VALUE_DICT_FILE):
        return {}
    try:
        with open(VALUE_DICT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_dictionary(data):
    """Сохраняет словарь правил в JSON-файл."""
    with open(VALUE_DICT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def add_entry(canonical_word, find_words_str):
    """Добавляет или обновляет правило в словаре."""
    dictionary = load_dictionary()
    # --- ИЗМЕНЕНИЕ ЗДЕСЬ ---
    # Разделяем строку по вашему разделителю
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
    Это самая эффективная структура для процесса обработки.
    """
    dictionary = load_dictionary()
    reverse_map = {}
    for canonical_word, find_words_list in dictionary.items():
        for find_word in find_words_list:
            if find_word:  # Доп. проверка на всякий случай
                reverse_map[find_word] = canonical_word
    return reverse_map