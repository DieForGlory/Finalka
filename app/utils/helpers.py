# app/utils/helpers.py
import re
from openpyxl.utils import column_index_from_string

ALLOWED_EXTENSIONS = {'xls','xlsx', 'xlsm'}


def allowed_file(filename):
    """Проверяет, имеет ли файл разрешенное расширение."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_header(header):
    """Приводит заголовок к нижнему регистру и удаляет все не-буквенно-цифровые символы."""
    if not isinstance(header, str):
        header = str(header)
    return re.sub(r'[\s\W_]+', '', header.lower())


def get_col_from_cell(cell_coord):
    """Извлекает буквенное обозначение колонки из координаты ячейки (например, 'A' из 'A5')."""
    if not cell_coord: return None
    match = re.match(r"([A-Z]+)", cell_coord.upper())
    return match.group(1) if match else None


def find_column_indices(worksheet, start_row, headers_to_find):
    """Находит индексы колонок для заданных заголовков."""
    indices = {}
    if not worksheet: return indices

    try:
        header_row = worksheet[start_row]
        normalized_map = {normalize_header(cell.value): cell.column for cell in header_row if cell.value}

        for key, target_header in headers_to_find.items():
            normalized_target = normalize_header(target_header)
            found_col = normalized_map.get(normalized_target)
            if found_col:
                indices[key] = found_col
    except (IndexError, TypeError):
        # Ошибка, если start_row не существует
        pass
    return indices
