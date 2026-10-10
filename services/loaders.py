import os
import yaml
from pathlib import Path

#Установка директорий
CHAR_DIR = Path("data/char")
ADV_DIR = Path("data/adv")
DEFAULT_CHAR_IMAGE = "assets/img/char/in_prog.png"
DEFAULT_ADV_IMAGE = "assets/img/adv/in_prog.png"

#Сервис загрузки персонажей
def load_characters():
    characters = [] #Формирование списка
    if not CHAR_DIR.exists(): #Проверка наличия директории(автосоздание лишнее)
        return characters
    
    for file_path in CHAR_DIR.glob("*.yaml"): #поиск нужных файлов и извлечение данных
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data:
                    #логика проверки существующего изображение или замена моксом
                    img_path = data.get("visual", {}).get("image_path", DEFAULT_CHAR_IMAGE)
                    #if not Path(img_path).exists():
                    if not img_path or not Path(img_path).exists():
                        img_path = DEFAULT_CHAR_IMAGE
                    if "visual" not in data:
                        data["visual"] = {}
                    data["visual"]["resolved_image_path"] = img_path
                    characters.append(data)
        except Exception as e:
            print(f"Ошибка загрузки персонажа из {file_path}: {e}")

    return characters

#Сервис загрузки приключений
def load_adventures():
    adventures = [] #Формирование списка
    if not ADV_DIR.exists(): #Проверка наличия директории(автосоздание лишнее)
        return adventures
    
    for file_path in ADV_DIR.glob("*.yaml"): #поиск нужных файлов и извлечение данных
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data:
                    #логика проверки существующего изображение или замена моксом
                    img_path = data.get("image_path", DEFAULT_ADV_IMAGE)
                    #if not Path(img_path).exists():
                    if not img_path or not Path(img_path).exists():
                        img_path = DEFAULT_ADV_IMAGE
                    data["resolved_image_path"] = img_path
                    adventures.append(data)
        except Exception as e:
            print(f"Ошибка загрузки приключений из {file_path}: {e}")

    return adventures