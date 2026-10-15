import os
import yaml
from pathlib import Path

#Установка директорий
CHAR_DIR = Path("data/char")
ADV_DIR = Path("data/adv")
PROMPTS_DIR = Path("data/prompts")
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

# Универсальная функция для получения жанра и правил мира конкретного приключения
def get_adventure_world_info(adventure_id: str) -> dict:
    """
    Ищет YAML-файл приключения по его id и возвращает словарь с жанром и правилами мира.
    Возвращает пустые значения, если приключение не найдено или секция отсутствует.
    """
    if not ADV_DIR.exists():
        return {"genre": [], "rules": ""}
    
    for file_path in ADV_DIR.glob("*.yaml"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                # Сверяем id приключения из файла с искомым
                if data and data.get("id") == adventure_id:
                    llm_settings = data.get("world", {}).get("llm", {})
                    return {
                        "genre": llm_settings.get("genre", []),
                        "rules": llm_settings.get("rules", "").strip()
                    }
        except Exception as e:
            print(f"Ошибка чтения файла {file_path} при поиске мира: {e}")
            
    return {"genre": [], "rules": ""}

def load_prompt(prompt_file: str) -> str:
    """Загружает текст Prompt из YAML-файла в data/prompts."""

    path = PROMPTS_DIR / prompt_file

    if not path.is_file():
        raise FileNotFoundError(f"Файл промпта не найден: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict) or not isinstance(data.get("Prompt"), str):
        raise ValueError(
            f"Файл {path.name} должен содержать строковое поле 'Prompt'"
        )

    return data["Prompt"]
    
def load_prompt_section(prompt_file: str, section_key: str) -> str:
    """Загружает конкретную секцию промпта из YAML-файла."""
    path = PROMPTS_DIR / prompt_file
    if not path.is_file():
        raise FileNotFoundError(f"Файл промпта не найден: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict) or section_key not in data:
        raise ValueError(f"В файле {path.name} отсутствует ключ '{section_key}'")

    return data[section_key]    