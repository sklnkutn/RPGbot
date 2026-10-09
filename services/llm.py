import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()  # Загрузка переменных окружения из файла .env

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")  # Получение URL Ollama из переменных окружения
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2") # Получение модели Ollama из переменных окружения
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "10"))

async def ask_llm(user_text: str) -> str:
    """Функция для отправки запроса к Ollama и получения ответа."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "user", "content": user_text}
        ],
        "stream": False
    }

    timeout = aiohttp.ClientTimeout(total=LLM_TIMEOUT)  # Установка таймаута для запроса

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(OLLAMA_URL, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("message", {}).get("content", "Нет ответа от LLM.")
                else:
                    return f"Ошибка при обращении к LLM: {response.status}"
            
    except aiohttp.ClientConnectorError:
        return "Ошибка подключения к LLM. Проверьте URL и доступность сервера." 
    except Exception as e:
        return f"Произошла ошибка при обращении к LLM: {e}"
