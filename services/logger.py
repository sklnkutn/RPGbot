# services/logger.py
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Папка для хранения лог-файлов
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Формат для общих логов конвейера и ошибок
APP_FORMATTER = logging.Formatter(
    fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Формат для аудита состояний (более чистый)
STATE_FORMATTER = logging.Formatter(
    fmt="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def _setup_app_logger() -> logging.Logger:
    logger = logging.getLogger("RPG_Engine")
    logger.setLevel(logging.DEBUG)  # Захватываем все уровни от DEBUG и выше
    logger.propagate = False

    if logger.handlers:
        return logger

    # 1. Вывод в консоль (stdout) для отладки во время разработки
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(APP_FORMATTER)
    logger.addHandler(console_handler)

    # 2. Вывод в основной файл логов с ротацией (максимум 5 файлов по 5 МБ)
    file_handler = RotatingFileHandler(
        LOGS_DIR / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(APP_FORMATTER)
    logger.addHandler(file_handler)

    return logger

def _setup_state_logger() -> logging.Logger:
    """Специальный логгер только для фиксации изменений параметров и статов персонажей."""
    logger = logging.getLogger("RPG_StateAudit")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    state_file_handler = RotatingFileHandler(
        LOGS_DIR / "state_changes.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    state_file_handler.setFormatter(STATE_FORMATTER)
    logger.addHandler(state_file_handler)

    return logger

# Экспортируем готовые инстансы
logger = _setup_app_logger()
state_logger = _setup_state_logger()