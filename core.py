import os
import hashlib
from collections import defaultdict
from logger import get_logger

# >>> ИЗМЕНЕНИЕ: Полный список директорий, которые следует пропускать
SKIP_DIRECTORIES = {
    # Общие системные/кэш пути
    os.path.join('AppData', 'Local', 'Temp'),
    os.path.join('AppData', 'Roaming'),
    os.path.join('AppData', 'Local', 'Microsoft', 'Windows', 'INetCache'),
    os.path.join('Local Settings', 'Temp'),  # Для старых версий Windows
    os.path.join('Windows', 'Temp'),

    # Кэш/Компоненты браузеров
    os.path.join('AppData', 'Local', 'Google', 'Chrome', 'User Data'),
    'Service Worker',
    'CacheStorage',
    'Code Cache',
    'Extensions',

    # Системные и программные файлы Windows
    'Program Files',
    'Program Files (x86)',
    '$RECYCLE.BIN',
    'System Volume Information',
    'Windows',
    'System32',

    # Игровые/Медиа библиотеки (Steam, Epic, т.п.)
    'SteamLibrary',
    os.path.join('steamapps', 'common'),
    os.path.join('steamapps', 'workshop'),
    'Epic Games',

    # Разработка и виртуальные среды
    '.git',
    '.svn',
    'node_modules',
    'venv',

    # macOS/Linux специфичные кэши
    os.path.join('Library', 'Caches'),
    '.Trash',
    '.cache',
    os.path.join('Users', 'Default')  # Системные профили
}


# <<< КОНЕЦ ИЗМЕНЕНИЯ


def calculate_file_hash(filepath, chunk_size=65536, gui=None, cancel_flag=None):
    """Вычисляет MD5 хеш файла"""
    logger = get_logger()
    md5_hash = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                # >>> ДОБАВЛЕНО: Проверка отмены во время хеширования
                if cancel_flag and cancel_flag():
                    return None
                # <<<
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except PermissionError as e:
        if gui:
            gui.permission_errors += 1
        logger.warning(f"Отказано в доступе при хешировании файла {filepath}: {e}")
        return None
    except Exception as e:
        logger.error(f"Ошибка хеширования файла {filepath}: {e}")
        return None


def find_duplicates(directory, extensions=None, recursive=True, gui=None, cancel_flag=None):
    """
    Находит дубликаты файлов в указанной директории.
    Поддерживает рекурсивное и нерекурсивное сканирование.
    >>> ИЗМЕНЕНИЕ: Добавлен аргумент cancel_flag
    """
    logger = get_logger()
    logger.log_scan_start(directory, extensions)

    files_by_size = defaultdict(list)
    total_files = 0

    if recursive:
        for root, dirs, files in os.walk(directory):
            # >>> ДОБАВЛЕНО: Проверка отмены в цикле обхода папок
            if cancel_flag and cancel_flag():
                return {}  # Возвращаем пустой результат при отмене
            # <<<

            # Пропускаем директории из SKIP_DIRECTORIES (с проверкой нижнего регистра)
            dirs[:] = [d for d in dirs if not any(
                skip_dir.lower() in os.path.join(root, d).lower().replace(os.sep, '/') or d.lower() == skip_dir.lower()
                for skip_dir in SKIP_DIRECTORIES)]

            for filename in files:
                filepath = os.path.join(root, filename)
                if extensions and not any(filename.lower().endswith(ext.lower()) for ext in extensions):
                    continue
                try:
                    file_size = os.path.getsize(filepath)
                    if file_size > 0:
                        files_by_size[file_size].append({
                            'path': filepath,
                            'name': filename,
                            'size': file_size
                        })
                        total_files += 1
                except PermissionError as e:
                    if gui:
                        gui.permission_errors += 1
                    logger.warning(f"Отказано в доступе к файлу {filepath}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Ошибка получения размера файла {filepath}: {e}")
                    continue
    else:
        for filename in os.listdir(directory):
            # >>> ДОБАВЛЕНО: Проверка отмены в нерекурсивном цикле
            if cancel_flag and cancel_flag():
                return {}
            # <<<

            filepath = os.path.join(directory, filename)
            if os.path.isdir(filepath):
                continue
            if extensions and not any(filename.lower().endswith(ext.lower()) for ext in extensions):
                continue
            try:
                file_size = os.path.getsize(filepath)
                if file_size > 0:
                    files_by_size[file_size].append({
                        'path': filepath,
                        'name': filename,
                        'size': file_size
                    })
                    total_files += 1
            except PermissionError as e:
                if gui:
                    gui.permission_errors += 1
                logger.warning(f"Отказано в доступе к файлу {filepath}: {e}")
                continue
            except Exception as e:
                logger.error(f"Ошибка получения размера файла {filepath}: {e}")
                continue

    logger.info(f"Этап 1 завершён. Проверено файлов: {total_files}")

    # >>> ДОБАВЛЕНО: Финальная проверка отмены после Этапа 1
    if cancel_flag and cancel_flag():
        return {}
    # <<<

    potential_duplicates = {size: files for size, files in files_by_size.items() if len(files) > 1}

    if not potential_duplicates:
        logger.info("Потенциальных дубликатов не найдено")
        return {}

    files_to_hash_count = sum(len(files) for files in potential_duplicates.values())
    logger.info(f"Найдено потенциальных дубликатов: {files_to_hash_count} файлов в {len(potential_duplicates)} группах")

    # === Этап 2: Хеширование для точного сравнения ===
    hashes = defaultdict(list)
    for files in potential_duplicates.values():
        for file_info in files:
            # >>> ДОБАВЛЕНО: Проверка отмены перед хешированием
            if cancel_flag and cancel_flag():
                return {}
            # <<<

            file_hash = calculate_file_hash(file_info['path'], gui=gui, cancel_flag=cancel_flag)

            # Если хеш вернулся None (из-за ошибки или отмены), пропускаем
            if file_hash:
                hashes[file_hash].append(file_info)

    duplicates = {h: files for h, files in hashes.items() if len(files) > 1}

    logger.info(f"Этап 2 завершён. Найдено {len(duplicates)} групп дубликатов")

    return duplicates