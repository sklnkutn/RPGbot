from nicegui import ui

# Глобальное состояние отладочного сервера (доступно для импорта)
debug_state = {
    "mode": "local"  # "local" (автономный мок) или "bridge" (облачный мост)
}

def setup_debug_page():
    """Регистрация страниц отладочного интерфейса"""
    
    @ui.page("/")
    def index():
        return ui.navigate.to("/debug")

    @ui.page("/debug")
    def debug_page():
        
        status_banner = ui.label().classes("text-sm font-mono q-mb-md text-center w-full")

        def refresh_ui_state():
            current_mode = debug_state["mode"]
            if current_mode == "local":
                status_banner.text = "🟢 Активный режим: Автономный мок (статические модели)"
                status_banner.classes(replace="text-sm font-mono q-mb-md text-center w-full text-green-400")
            else:
                status_banner.text = "🔵 Активный режим: Облачный мост (файловый перехватчик outputs ↔ inputs)"
                status_banner.classes(replace="text-sm font-mono q-mb-md text-center w-full text-blue-400")

        with ui.column().classes("w-full max-w-2xl mx-auto q-pa-lg items-center justify-center h-screen"):
            
            ui.label("🛠️ Панель отладки и режимов мока").classes("text-2xl font-bold q-mb-xs text-white")
            ui.label("Управление поведением заглушек движка").classes("text-xs text-gray-400 q-mb-lg")
            
            refresh_ui_state()

            with ui.row().classes("w-full q-col-gutter-md q-mb-lg"):
                
                # Карточка 1: Локальный мок
                with ui.card().classes("col cursor-pointer p-6 items-center bg-grey-9 hover:bg-grey-8 transition border border-gray-700") as card_local:
                    ui.icon("settings_ethernet", size="md").classes("text-green-400 q-mb-sm")
                    ui.label("1. Автономный мок").classes("font-bold text-white text-base q-mb-xs")
                    ui.label("Отвечает заготовленными списками моделей. Подходит для верстки и логики UI.").classes("text-xs text-gray-400 text-center")
                    
                    def set_local_mode():
                        debug_state["mode"] = "local"
                        refresh_ui_state()
                        ui.notify("Включен режим: Автономный мок", type="positive", position="top")

                    card_local.on("click", set_local_mode)

                # Карточка 2: Облачный мост
                with ui.card().classes("col cursor-pointer p-6 items-center bg-grey-9 hover:bg-grey-8 transition border border-gray-700") as card_bridge:
                    ui.icon("sync_alt", size="md").classes("text-blue-400 q-mb-sm")
                    ui.label("2. Облачный мост").classes("font-bold text-white text-base q-mb-xs")
                    ui.label("Перенаправляет запросы через папки outputs/ и inputs/ для работы с Colab/Kaggle.").classes("text-xs text-gray-400 text-center")
                    
                    def set_bridge_mode():
                        debug_state["mode"] = "bridge"
                        refresh_ui_state()
                        ui.notify("Включен режим: Облачный мост", type="info", position="top")

                    card_bridge.on("click", set_bridge_mode)

            ui.separator().classes("w-full q-my-md bg-gray-8")