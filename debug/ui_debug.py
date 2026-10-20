# debug/ui_debug.py
from nicegui import ui
from pathlib import Path
import json

debug_state = {
    "mode": "local"  # "local" или "bridge"
}

# Очередь активных задач
pending_tasks = []

def setup_debug_page():
    @ui.page("/")
    def index():
        return ui.navigate.to("/debug")

    @ui.page("/debug")
    def debug_page():
        with ui.column().classes("w-full max-w-4xl mx-auto q-pa-lg"):
            
            ui.label("🛠️ Панель управления отладкой и мок-серверами").classes("text-2xl font-bold text-white")
            
            # Статус-баннер
            status_banner = ui.label().classes("text-sm font-mono q-my-sm")
            
            def update_status():
                if debug_state["mode"] == "local":
                    status_banner.text = "🟢 Режим: АВТОНОМНЫЙ МОК (Умная генерация JSON/текста на лету)"
                    status_banner.classes(replace="text-sm font-mono text-green-400")
                else:
                    status_banner.text = "🔵 Режим: ОБЛАЧНЫЙ МОСТ (Ожидание ответов в debug/input/)"
                    status_banner.classes(replace="text-sm font-mono text-blue-400")

            update_status()

            # Переключатели режимов
            with ui.row().classes("w-full q-gutter-md q-my-md"):
                def set_local():
                    debug_state["mode"] = "local"
                    update_status()
                    ui.notify("Режим изменен: Автономный мок", type="positive")

                def set_bridge():
                    debug_state["mode"] = "bridge"
                    update_status()
                    ui.notify("Режим изменен: Облачный мост", type="info")

                ui.button("Автономный умный мок", icon="bolt", on_click=set_local).props("color=green outline")
                ui.button("Облачный мост (Outputs ↔ Inputs)", icon="sync_alt", on_click=set_bridge).props("color=blue outline")

            ui.separator().classes("q-my-md")

            # Секция Очереди задач (Live Tasks)
            ui.label("📋 Очередь перехваченных запросов (Bridge Tasks)").classes("text-lg font-bold text-gray-300")
            ui.label("GET моделей: отправьте файл задания из debug/output на Kaggle и верните реальный JSON-ответ с тем же именем в debug/input. Ollama POST: JSON-ответ. ComfyUI: JSON-ответ и указанный файл изображения.").classes("text-xs text-gray-400")

            tasks_container = ui.column().classes("w-full q-mt-sm")

            def refresh_tasks():
                tasks_container.clear()
                if not pending_tasks:
                    with tasks_container:
                        ui.label("Запросов пока нет. Запустите ход в боте.").classes("text-xs text-gray-500 italic")
                    return

                # Показываем последние 10 задач
                for task in reversed(pending_tasks[-10:]):
                    with tasks_container:
                        card_color = "bg-grey-9" if task["status"] != "waiting" else "bg-blue-950 border border-blue-500"
                        with ui.card().classes(f"w-full q-pa-sm {card_color} text-white"):
                            with ui.row().classes("w-full justify-between items-center"):
                                with ui.row().classes("items-center q-gutter-x-sm"):
                                    badge_color = "green" if task["status"] == "completed" or task["status"] == "auto_mocked" else "orange"
                                    ui.badge(task["status"], color=badge_color)
                                    ui.label(task["id"]).classes("font-mono text-xs font-bold")
                                ui.label(task["endpoint"]).classes("text-xs text-gray-400")
                            
                            ui.label(f"Превью: {task.get('preview', '')}").classes("text-[11px] text-gray-300 truncate w-full")

                            # Если задача ждет ответа — даем кнопку быстрой вставки JSON прямо из браузера!
                            if task["status"] == "waiting":
                                with ui.expansion("Вставить ответ вручную (Quick Inject)", icon="edit").classes("w-full text-xs text-blue-300"):
                                    resp_input = ui.textarea(placeholder='{"message": {"content": "Ответ модели..."}}').props("outlined dense rows=3 dark").classes("w-full")
                                    
                                    def make_submit_handler(filename, inp):
                                        def submit():
                                            try:
                                                parsed = json.loads(inp.value)
                                                target = Path("debug/input") / filename
                                                with open(target, "w", encoding="utf-8") as f:
                                                    json.dump(parsed, f, ensure_ascii=False, indent=2)
                                                ui.notify(f"Ответ сохранен в {filename}!", type="positive")
                                            except Exception as ex:
                                                ui.notify(f"Ошибка JSON: {ex}", type="negative")
                                        return submit

                                    ui.button("Отправить в движок", icon="send", on_click=make_submit_handler(task["id"], resp_input)).props("size=sm color=primary")

            # Таймер автообновления списка задач каждые 2 секунды
            ui.timer(2.0, refresh_tasks)