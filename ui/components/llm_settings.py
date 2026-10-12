from nicegui import ui

def create_llm_settings():
    """Создает иконку и селект для LLM."""
    ui.icon("psychology", size="sm").classes("text-gray-400")
    llm_select = (
        ui.select(
            options=["llama3:8b", "mistral:7b", "gemma2:9b"],
            value="llama3:8b",
            label="Модель LLM"
        )
        .classes("col")
        .props("outlined dense dark")
    )
    return llm_select