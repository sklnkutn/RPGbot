import os
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()  # Загрузка переменных окружения из файла .env

OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "10"))
COMFY_PORT = os.getenv("COMFY_PORT", "8188")
COMFY_TIMEOUT = int(os.getenv("COMFY_TIMEOUT", "10"))

def get_server_url(server: str, endpoint: str = "") -> str:
    """
    Составляет базовый адрес обращения от сервиса (ollama, comfy) + эндпоинт.
    """
    server = server.lower()  # нормализация
    
    if server == "ollama":
        port = OLLAMA_PORT
    elif server == "comfy":
        port = COMFY_PORT
    else:
        raise ValueError(f"Неизвестный server: {server}")
        
    base_url = f"http://localhost:{port}"
    return f"{base_url}/{endpoint.lstrip('/')}" if endpoint else base_url

def _get_timeout_for_server(server: str) -> int:
    """Внутренний помощник для выбора правильного таймаута."""
    server = server.lower()
    if server == "comfy":
        return COMFY_TIMEOUT
    return OLLAMA_TIMEOUT

async def _safe_request_wrapper(request_coro, server: str, timeout_seconds: int):
    """Единообразная обработка сетевых ошибок и таймаутов."""
    try:
        return await request_coro
    except aiohttp.ClientConnectorError:
        return f"Ошибка подключения к сервису '{server}'. Проверьте, запущен ли локальный сервер." 
    except asyncio.TimeoutError:
        return f"Превышено время ожидания ответа от '{server}' (таймаут {timeout_seconds}с)."
    except Exception as e:
        return f"Произошла непредвиденная ошибка при запросе к '{server}': {e}"

async def _execute_get(url: str, client_timeout: aiohttp.ClientTimeout, server: str):
    """Выполняет непосредственное открытие сессии и GET-запрос."""
    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                return f"Ошибка сервера ({server}): получен статус {response.status}"

async def send_http_get(url: str, server: str, timeout_seconds: int = 5) -> dict | list | str:
    """Главная функция для отправки GET-запросов."""
    client_timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    
    return await _safe_request_wrapper(
        _execute_get(url, client_timeout, server), 
        server, 
        timeout_seconds
    )

async def _execute_post(url: str, payload: dict, client_timeout: aiohttp.ClientTimeout, server: str):
    """Выполняет непосредственное открытие сессии и POST-запрос с переданным payload."""
    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                return await response.json()
            else:
                return f"Ошибка сервера ({server}): получен статус {response.status}"

async def send_http_post(url: str, payload: dict, server: str = "ollama") -> dict | list | str:
    """Главная функция для отправки POST-запросов."""
    # Используем готовый хелпер для выбора таймаута под конкретный сервер
    timeout_seconds = _get_timeout_for_server(server)
    client_timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    
    return await _safe_request_wrapper(
        _execute_post(url, payload, client_timeout, server), 
        server, 
        timeout_seconds
    )

async def get_comfy_models(model_type: str = "checkpoints") -> list | str:
    """
    Запрашивает список доступных моделей заданного типа из ComfyUI. Например: checkpoints, lora, vae и т.д.
    """
    # Формируем путь, например: /models/checkpoints
    endpoint = f"models/{model_type}"
    url = get_server_url("comfy", endpoint)
    # Используем наш быстрый GET-транспорт (с коротким таймаутом, т.к. это метаданные)
    response = await send_http_get(url, server="comfy", timeout_seconds=5)
    # Если сервер вернул ошибку (строку), просто передаем её дальше
    if isinstance(response, str):
        return response
    # Если вернулся успешный JSON, извлекаем список моделей(в зависимости от версии ComfyUI структура может отличаться, обычно это список строк или словарь)
    if isinstance(response, list):
        return response
    elif isinstance(response, dict):
        # Иногда структура может быть в виде {"models": [...]} или ключей
        return response.get("models", list(response.keys()))
        
    return []