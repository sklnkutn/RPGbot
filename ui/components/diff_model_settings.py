import asyncio
from nicegui import ui
from services.server_request import get_comfy_models

def create_diff_model_settings():
    """
    Создает селект моделей с автоматическим фоновым ожиданием через сервисный слой.
    """
    checkpoint_select = (
        ui.select(
            options=["Ожидание подключения к серверу..."],
            value="Ожидание подключения к серверу...",
            label="Модель визуализации"
        )
        .classes("col")
        .props("outlined dense dark")
    )
    ui.icon("image", size="sm").classes("text-gray-400")

    # Флаг готовности для валидации при старте игры
    checkpoint_select.is_ready = False

    async def init_models():
        # Запускаем запрос с включенным ретраем (12 попыток по 5 секунд = 1 минута ожидания)
        response = await get_comfy_models("checkpoints", retry=True, max_attempts=12, delay=5)
        
        if isinstance(response, list) and response:
            checkpoint_select.options = response
            checkpoint_select.value = response[0]
            checkpoint_select.is_ready = True
            ui.notify("Модели визуализации успешно загружены", type="positive", position="top", timeout=2000)
        elif isinstance(response, list) and not response:
            checkpoint_select.options = ["модели не обнаружены"]
            checkpoint_select.value = "модели не обнаружены"
            checkpoint_select.is_ready = False
            ui.notify("Внимание: в ComfyUI не найдены файлы моделей", type="warning", position="top")
        else:
            # Если даже после всех попыток сервер недоступен
            checkpoint_select.options = ["Сервер недоступен"]
            checkpoint_select.value = "Сервер недоступен"
            checkpoint_select.is_ready = False
            ui.notify(f"Не удалось подключиться к ComfyUI: {response}", type="negative", position="top")

    # ui.timer автоматически привязывает выполнение к контексту текущей страницы/клиента,
    # поэтому ui.notify и обновление элементов будут работать без ошибок.
    ui.timer(0.1, init_models, once=True)

    return checkpoint_select