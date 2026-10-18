import os
import yaml
import json
import aiohttp
from services.server_request import get_server_url
from pathlib import Path

#Установка директорий
CHAR_DIR = Path("data/char")
ADV_DIR = Path("data/adv")
PROMPTS_DIR = Path("data/prompts")
DEFAULT_CHAR_IMAGE = "assets/img/char/in_prog.png"
DEFAULT_ADV_IMAGE = "assets/img/adv/in_prog.png"
WORKFLOW_PATH = Path("data/comfy_workflow/bot_workflow.json")


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

def load_character_data(char_id: str) -> dict: #дописать функцию загрузки параметров из YAML
    """Загрузка полных данных конкретного персонажа из YAML-файла по его id"""
    if not CHAR_DIR.exists():
        return {}
    
    # Ищем среди всех файлов персонажей
    for file_path in CHAR_DIR.glob("*.yaml"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and data.get("id") == char_id:
                    # Нормализуем путь к картинке на случай, если он запрашивается отдельно
                    raw_img = data.get("visual", {}).get("image_path", DEFAULT_CHAR_IMAGE)
                    resolved_img = _resolve_image_path(raw_img, DEFAULT_CHAR_IMAGE)
                    
                    if "visual" not in data:
                        data["visual"] = {}
                    data["visual"]["resolved_image_path"] = resolved_img
                    
                    # Извлекаем возраст и прозвище сделланными безопасными (если их нет — вернется None или текст по умолчанию)
                    bio_data = data.get("bio", {})
                    
                    # Возвращаем обогащенный словарь с удобной структурой
                    return {
                        "id": data.get("id"),
                        "name": data.get("name", "Безымянный"),
                        "alias": data.get("alias"),  # Прозвище (может быть None)
                        "age": bio_data.get("age", "не указан"),
                        "gender": bio_data.get("gender", "не указан"),
                        "visual": data.get("visual", {}),
                        "bio": bio_data,
                        "personality_traits": bio_data.get("personality_traits", []),
                        "description": bio_data.get("description", "")
                    }
        except Exception as e:
            print(f"Ошибка чтения файла персонажа {file_path}: {e}")
            
    # Если персонаж с таким ID не найден
    print(f"[Loader Warning] Персонаж с id '{char_id}' не найден в директории {CHAR_DIR}.")
    return {}
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

def _load_workflow_template() -> dict:
    """Загружает шаблон рабочего процесса ComfyUI из файла."""
    if not WORKFLOW_PATH.exists():
        raise FileNotFoundError(f"Файл workflow не найден: {WORKFLOW_PATH}")
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

async def _download_comfy_image(filename: str, subfolder: str, folder_type: str, target_path: Path) -> bool:
    """Скачивает сгенерированное изображение из ComfyUI /view и сохраняет локально."""
    base_url = get_server_url("comfy", "view")
    params = {
        "filename": filename,
        "subfolder": subfolder,
        "type": folder_type
    }
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(base_url, params=params) as resp:
                if resp.status == 200:
                    image_bytes = await resp.read()
                    with open(target_path, "wb") as f:
                        f.write(image_bytes)
                    return True
                else:
                    print(f"[ComfyUI Download Error]: статус {resp.status}")
                    return False
    except Exception as e:
        print(f"[ComfyUI Download Error]: {e}")
        return False
