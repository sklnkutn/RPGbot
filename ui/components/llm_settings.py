import asyncio
from nicegui import ui
from services.server_request import get_ollama_models

def create_llm_settings():
    """
    Создает селект моделей LLM с автоматическим фоновым ожиданием через Ollama.
    """
    ui.icon("psychology", size="sm").classes("text-gray-400")
    llm_select = (
        ui.select(
            options=["Ожидание подключения к серверу..."],
            value="Ожидание подключения к серверу...",
            label="Модель LLM"
        )
        .classes("col")
        .props("outlined dense dark")
    )

    # Флаг готовности для валидации при старте игры (если потребуется)
    llm_select.is_ready = False

    async def init_models():
        # Запускаем запрос с ретраями (12 попыток по 5 секунд = 1 минута ожидания)
        response = await get_ollama_models(retry=True, max_attempts=12, delay=5)
        
        if isinstance(response, list) and response:
            llm_select.options = response
            llm_select.value = response[0]
            llm_select.is_ready = True
            ui.notify("Модели LLM успешно загружены", type="positive", position="top", timeout=2000)
        elif isinstance(response, list) and not response:
            llm_select.options = ["модели не обнаружены"]
            llm_select.value = "модели не обнаружены"
            llm_select.is_ready = False
            ui.notify("Внимание: в Ollama не найдены установленные модели", type="warning", position="top")
        else:
            # Если после всех попыток сервер недоступен или вернулась ошибка
            llm_select.options = ["Сервер недоступен"]
            llm_select.value = "Сервер недоступен"
            llm_select.is_ready = False
            ui.notify(f"Не удалось подключиться к Ollama: {response}", type="negative", position="top")

    # Автоматический запуск инициализации при монтировании компонента на странице
    ui.timer(0.1, init_models, once=True)

    return llm_select