import json
import os
from datetime import datetime
from pathlib import Path

# Папка для сохранения логов запросов в режиме отладки
DEBUG_LOGS_DIR = Path("debug/output")

def save_request_json(endpoint_name: str, payload: dict) -> str:
    """
    Сохраняет входящий JSON-запрос в файл для отладки.
    Возвращает путь к сохраненному файлу.
    """
    DEBUG_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Формируем уникальное имя файла с таймстампом
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    safe_endpoint_name = endpoint_name.strip("/").replace("/", "_")
    filename = f"{timestamp}_{safe_endpoint_name}.json"
    file_path = DEBUG_LOGS_DIR / filename
    
    # Записываем JSON с отступами и поддержкой кириллицы (ensure_ascii=False)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)
        
    print(f"[Mock Server] Запрос сохранен в файл: {file_path}")
    return str(file_path)