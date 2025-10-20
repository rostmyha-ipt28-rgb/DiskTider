# logger.py
import os
import logging
from datetime import datetime


class DiskTiderLogger:
    """Логгер для DiskTider с записью в файл и консоль"""

    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self.logger = None
        self.log_file = None
        self._setup_logger()

    def _setup_logger(self):
        """Настраивает логгер"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = os.path.join(self.log_dir, f"scan_{timestamp}.log")

        self.logger = logging.getLogger('DiskTider')
        self.logger.setLevel(logging.DEBUG)

        self.logger.handlers.clear()

        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def debug(self, message):
        self.logger.debug(message)

    def log_separator(self):
        self.logger.info("=" * 80)

    def log_scan_start(self, directory, extensions=None):
        self.log_separator()
        self.info("НАЧАЛО СКАНИРОВАНИЯ")
        self.log_separator()
        self.info(f"Директория: {directory}")
        if extensions:
            self.info(f"Фильтр расширений: {', '.join(extensions)}")
        else:
            self.info("Фильтр расширений: все файлы")

    def log_deletion_start(self, mode, target_extension=None):
        self.log_separator()
        self.info("НАЧАЛО УДАЛЕНИЯ")
        self.log_separator()
        mode_text = {
            'trash': 'Перемещение в корзину',
            'delete': 'Удаление навсегда',
            'preview': 'Режим предпросмотра'
        }
        self.info(f"Режим: {mode_text.get(mode, mode)}")
        if target_extension:
            self.info(f"Целевое расширение: {target_extension}")

    def log_deletion_error(self, filepath, error):
        self.error(f"Не удалось удалить {filepath}: {error}")

    def log_deletion_results(self, deleted_count, freed_space_str):
        self.log_separator()
        self.info("РЕЗУЛЬТАТЫ УДАЛЕНИЯ")
        self.log_separator()
        self.info(f"Удалено файлов: {deleted_count}")
        self.info(f"Освобождено места: {freed_space_str}")

    def log_scan_complete(self):
        self.log_separator()
        self.info("СКАНИРОВАНИЕ ЗАВЕРШЕНО")
        self.log_separator()

# Глобальный экземпляр логгера
_logger_instance = None


def get_logger():
    """Получить глобальный экземпляр логгера"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = DiskTiderLogger()
    return _logger_instance