import os
from dotenv import load_dotenv
from aiohttp import web
from nicegui import app, ui
from ui_debug import setup_debug_page, debug_state
from mode_local import get_local_ollama_models, get_local_comfy_models

load_dotenv()
DEBUG_PORT = int(os.getenv("DEBUG_PORT", 8086))

# Инициализируем UI страниц отладки
setup_debug_page()

# --- ОБРАБОТЧИКИ МОК-СЕРВЕРОВ ---

async def handle_ollama_tags(request: web.Request):
    """Эндпоинт для Ollama (/api/tags)"""
    print(f"[Mock Server] GET /api/tags (Ollama). Текущий режим: {debug_state['mode']}")
    
    if debug_state["mode"] == "local":
        response_data = get_local_ollama_models()
        return web.json_response(response_data)
    else:
        # Режим bridge (пока заглушка)
        return web.json_response({"models": [{"name": "bridge-mode-model"}]})


async def handle_comfy_models(request: web.Request):
    """Эндпоинт для ComfyUI (/models/checkpoints)"""
    print(f"[Mock Server] GET /models/checkpoints (ComfyUI). Текущий режим: {debug_state['mode']}")
    
    if debug_state["mode"] == "local":
        response_data = get_local_comfy_models()
        return web.json_response(response_data)
    else:
        # Режим bridge (пока заглушка)
        return web.json_response(["bridge-mode-checkpoint.safetensors"])


@app.on_startup
async def start_mock_servers():
    """Запускает фоновые aiohttp серверы на портах Ollama (11434) и ComfyUI (8188)"""
    
    # 1. Сервер Ollama (порт 11434)
    ollama_app = web.Application()
    ollama_app.router.add_get("/api/tags", handle_ollama_tags)
    ollama_runner = web.AppRunner(ollama_app)
    await ollama_runner.setup()
    ollama_site = web.TCPSite(ollama_runner, "localhost", 11434)
    await ollama_site.start()
    print("=== [Mock Server] Запущен на порту 11434 (Ollama) ===")

    # 2. Сервер ComfyUI (порт 8188)
    comfy_app = web.Application()
    comfy_app.router.add_get("/models/checkpoints", handle_comfy_models)
    comfy_runner = web.AppRunner(comfy_app)
    await comfy_runner.setup()
    comfy_site = web.TCPSite(comfy_runner, "localhost", 8188)
    await comfy_site.start()
    print("=== [Mock Server] Запущен на порту 8188 (ComfyUI) ===")


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="RPG Bot Debug Panel",
        port=DEBUG_PORT,
        reload=True,
        dark=True
    )