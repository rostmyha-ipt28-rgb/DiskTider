# utils.py
import os
import re
from logger import get_logger

# >>> ВОЗВРАЩАЕМ send2trash
try:
    from send2trash import send2trash

    TRASH_AVAILABLE = True
except ImportError:
    TRASH_AVAILABLE = False
    print("⚠️ send2trash не установлен. Используйте: pip install send2trash")


# <<< КОНЕЦ ИЗМЕНЕНИЯ


def format_size(size_bytes):
    """Форматирует размер файла в читаемый вид"""
    if size_bytes < 0:
        return "0 Б"

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
        r'\s+\d+$',  # пробел и цифра в конце
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


def _normalize_path_long(filepath):
    """
    Нормализует путь, добавляя префикс \\\\?\\ для поддержки длинных путей (MAX_PATH)
    в os.remove, но не для send2trash.
    """
    if os.name == 'nt':
        filepath = os.path.normpath(filepath) # Сначала нормализуем разделители
        if not filepath.startswith('\\\\?\\'):
            if filepath.startswith('\\\\'):
                # UNC путь (\\server\share)
                return '\\\\?\\UNC\\' + filepath[2:]
            return '\\\\?\\' + filepath
    return filepath

def delete_files_by_list(files_to_delete, mode='trash', dry_run=False):
    """
    Удаляет файлы из списка.

    Args:
        files_to_delete: список словарей с ключами 'path', 'name', 'size'
        mode: 'trash' (в корзину) или 'delete' (навсегда)
        dry_run: если True, только показывает что будет удалено без реального удаления

    Returns:
        tuple: (deleted_count, freed_space_str, errors_list)
    """
    logger = get_logger()

    if dry_run:
        logger.info("🔍 РЕЖИМ ПРЕДПРОСМОТРА (DRY RUN) - файлы не будут удалены")
        mode = 'preview'

    logger.log_deletion_start(mode)

    deleted_count = 0
    freed_space = 0
    errors = []

    for file_info in files_to_delete:
        original_filepath = file_info['path']

        # >>> ИЗМЕНЕНИЕ: Нормализуем путь для единообразных разделителей.
        # Это помогает избежать ошибок даже без префикса MAX_PATH.
        normalized_for_trash = os.path.normpath(original_filepath)
        # <<<

        if dry_run:
            # Просто логируем, что файл будет удалён
            logger.info(f"[ПРЕДПРОСМОТР] Будет удалён: {original_filepath}")
            deleted_count += 1
            freed_space += file_info['size']
            continue

        try:
            if mode == 'trash' and TRASH_AVAILABLE:
                # Используем send2trash с путем, нормализованным только по разделителям
                send2trash(normalized_for_trash)
                logger.info(f"Перемещён в корзину: {original_filepath}")
            else:
                # Необратимое удаление (os.remove требует префикс для MAX_PATH)
                normalized_filepath_max_path = _normalize_path_long(original_filepath)
                os.remove(normalized_filepath_max_path)
                logger.info(f"Удалён навсегда: {original_filepath}")

            deleted_count += 1
            freed_space += file_info['size']

        except FileNotFoundError:
            error_msg = f"Файл не найден: {original_filepath}"
            logger.log_deletion_error(original_filepath, error_msg)
            errors.append(error_msg)
        except PermissionError as e:
            error_msg = f"Отказано в доступе: {str(e)}"
            logger.log_deletion_error(original_filepath, error_msg)
            errors.append(error_msg)
        except Exception as e:
            # Логгирование ошибки в том формате, в каком она пришла
            error_msg = f"Ошибка удаления: {type(e).__name__}: {str(e)}"
            logger.log_deletion_error(original_filepath, error_msg)
            errors.append(error_msg)

    freed_space_str = format_size(freed_space)

    if dry_run:
        logger.info(f"[ПРЕДПРОСМОТР] Будет удалено: {deleted_count} файлов")
        logger.info(f"[ПРЕДПРОСМОТР] Будет освобождено: {freed_space_str}")
    else:
        logger.log_deletion_results(deleted_count, freed_space_str)

    return deleted_count, freed_space_str, errors