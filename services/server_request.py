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

async def _fetch_models_with_retry(url: str, server: str, parse_func, retry: bool, max_attempts: int, delay: int) -> list | str:
    """Общий хелпер для выполнения запроса с ретраями и разбором ответа."""
    attempts = max_attempts if retry else 1
    
    for attempt in range(1, attempts + 1):
        response = await send_http_get(url, server=server, timeout_seconds=5)
        
        # Если пришел успешный ответ (не строка с ошибкой)
        if not isinstance(response, str):
            parsed_result = parse_func(response)
            if parsed_result is not None:
                return parsed_result
                
        # Если это ошибка или распарсить не удалось, ждем и повторяем
        if attempt < attempts:
            await asyncio.sleep(delay)
        else:
            # Возвращаем текст последней ошибки, если пришла строка, иначе дефолт
            return response if isinstance(response, str) else "модели не обнаружены"
            
    return "модели не обнаружены"

async def get_comfy_models(model_type: str = "checkpoints", retry: bool = False, max_attempts: int = 10, delay: int = 5) -> list | str:
    """Запрашивает список доступных моделей из ComfyUI."""
    url = get_server_url("comfy", f"models/{model_type}")
    
    def parse_comfy(response):
        if isinstance(response, list):
            return response
        elif isinstance(response, dict):
            return response.get("models", list(response.keys()))
        return None

    return await _fetch_models_with_retry(url, "comfy", parse_comfy, retry, max_attempts, delay)

async def get_ollama_models(retry: bool = False, max_attempts: int = 10, delay: int = 5) -> list | str:
    """Запрашивает список доступных локальных моделей из Ollama через /api/tags."""
    url = get_server_url("ollama", "api/tags")
    
    def parse_ollama(response):
        if isinstance(response, dict) and "models" in response:
            models = [m.get("name") for m in response["models"] if m.get("name")]
            return models if models else ["модели не обнаружены"]
        return None

    return await _fetch_models_with_retry(url, "ollama", parse_ollama, retry, max_attempts, delay)