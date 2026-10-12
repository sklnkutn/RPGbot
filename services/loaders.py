import os
import yaml
from pathlib import Path

#Установка директорий
CHAR_DIR = Path("data/char")
ADV_DIR = Path("data/adv")
DEFAULT_CHAR_IMAGE = "assets/img/char/in_prog.png"
DEFAULT_ADV_IMAGE = "assets/img/adv/in_prog.png"

def _resolve_image_path(raw_path: str, default_path: str) -> str:
    """Проверяет существование файла и возвращает корректный веб-путь со слэшем."""
    path_obj = Path(raw_path)
    
    # Если путь из YAML не существует на диске, используем дефолтный
    if not raw_path or not path_obj.exists():
        path_obj = Path(default_path)
        
    # Если даже дефолтный файл отсутствует, возвращаем как есть (или пустую строку)
    resolved = str(path_obj).replace("\\", "/") # Нормализация слэшей для Windows
    
    # Главное: путь должен начинаться с '/', чтобы ссылаться на app.add_static_files
    if not resolved.startswith("/"):
        resolved = f"/{resolved}"
        
    return resolved

# Сервис загрузки персонажей
def load_characters():
    characters = []
    if not CHAR_DIR.exists():
        return characters
    
    for file_path in CHAR_DIR.glob("*.yaml"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data:
                    raw_img = data.get("visual", {}).get("image_path", DEFAULT_CHAR_IMAGE)
                    resolved_img = _resolve_image_path(raw_img, DEFAULT_CHAR_IMAGE)
                    
                    if "visual" not in data:
                        data["visual"] = {}
                    data["visual"]["resolved_image_path"] = resolved_img
                    characters.append(data)
        except Exception as e:
            print(f"Ошибка загрузки персонажа из {file_path}: {e}")

    return characters

# Сервис загрузки приключений
def load_adventures():
    adventures = []
    if not ADV_DIR.exists():
        return adventures
    
    for file_path in ADV_DIR.glob("*.yaml"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data:
                    raw_img = data.get("image_path", DEFAULT_ADV_IMAGE)
                    resolved_img = _resolve_image_path(raw_img, DEFAULT_ADV_IMAGE)
                    
                    data["resolved_image_path"] = resolved_img
                    adventures.append(data)
        except Exception as e:
            print(f"Ошибка загрузки приключений из {file_path}: {e}")

    return adventures