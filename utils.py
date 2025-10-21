# utils.py
import os
import re
from logger import get_logger

# >>> ИЗМЕНЕНИЕ: Полностью отключаем send2trash.
TRASH_AVAILABLE = False


# <<< КОНЕЦ ИЗМЕНЕНИЯ


def format_size(size_bytes):
    """Форматирует размер файла в читаемый вид"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} ТБ"


def get_file_priority(filename):
    """
    Определяет приоритет файла для сохранения.
    Возвращает число: чем меньше, тем выше приоритет.
    """
    filename_lower = filename.lower()

    bad_patterns = [
        r'\(\d+\)',  # (1), (2), (3)
        r'\s+\d+',  # пробел и цифра в конце
        r'copy',
        r'копия',
        r'\s-\scopy',
        r'\s-\sкопия',
    ]

    penalty = 0
    for pattern in bad_patterns:
        if re.search(pattern, filename_lower):
            penalty += 10

    penalty += len(filename) * 0.01

    return penalty


def _normalize_path(filepath):
    """Нормализует путь для лучшей совместимости с Windows API (поддержка MAX_PATH)."""
    if os.name == 'nt':
        filepath = os.path.normpath(filepath)
        if not filepath.startswith('\\\\?\\'):
            if filepath.startswith('\\\\'):
                # UNC путь
                return '\\\\?\\UNC\\' + filepath[2:]
            return '\\\\?\\' + filepath
    return filepath


def delete_files_by_list(files_to_delete):
    """
    Удаляет файлы из списка с помощью os.remove (необратимо).
    """
    logger = get_logger()

    # >>> ИЗМЕНЕНИЕ: Режим всегда 'delete'
    mode = 'delete'
    logger.log_deletion_start(mode)
    # <<< КОНЕЦ ИЗМЕНЕНИЯ

    deleted_count = 0
    freed_space = 0

    for file_info in files_to_delete:
        original_filepath = file_info['path']

        # Для os.remove используем нормализованный путь с префиксом \\?\
        normalized_filepath = _normalize_path(original_filepath)

        try:
            # >>> ИЗМЕНЕНИЕ: Только необратимое удаление
            os.remove(normalized_filepath)
            logger.info(f"Удалён навсегда: {original_filepath}")
            # <<< КОНЕЦ ИЗМЕНЕНИЯ

            deleted_count += 1
            freed_space += file_info['size']
        except Exception as e:
            logger.log_deletion_error(original_filepath, str(e))

    freed_space_str = format_size(freed_space)
    logger.log_deletion_results(deleted_count, freed_space_str)

    return deleted_count, freed_space_str