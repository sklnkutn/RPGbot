# debug/main_debug.py
import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from aiohttp import web
from nicegui import app, ui

from ui_debug import setup_debug_page, debug_state, pending_tasks
from mode_local import (
    get_local_ollama_models, 
    get_local_comfy_models, 
    generate_smart_ollama_response
)
from save_request_json import save_request_json

load_dotenv()
DEBUG_PORT = int(os.getenv("DEBUG_PORT", 8189))
INPUT_DIR = Path("debug/input")
INPUT_DIR.mkdir(parents=True, exist_ok=True)
COMFY_TASKS = {}
COMFY_IMAGES = {}

# --- ВСПОМОГАТЕЛЬНЫЙ МЕХАНИЗМ МОСТА (BRIDGE WAITER) ---

async def wait_for_input_response(filename: str, task_info: dict, timeout_seconds: int = 600) -> dict:
    """
    Ожидает появления файла с таким же именем в папке debug/input/.
    После обнаружения считывает его, удаляет из input/ и возвращает спарсенный JSON.
    """
    target_file = INPUT_DIR / filename
    start_time = asyncio.get_event_loop().time()
    task_info["status"] = "waiting"

    print(f"[Bridge Mode] Ожидание файла ответа: {target_file}")

    while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
        if target_file.exists():
            try:
                # Даем файлу 100мс на случай, если операционная система еще завершает запись
                await asyncio.sleep(0.1)
                with open(target_file, "r", encoding="utf-8") as f:
                    response_json = json.load(f)

                task_info["status"] = "completed"
                # Удаляем отработанный файл из input, чтобы не путать следующие запросы
                try:
                    target_file.unlink()
                except Exception:
                    pass

                print(f"[Bridge Mode] Ответ получен и отправлен движку: {filename}")
                return response_json
            except Exception as e:
                print(f"[Bridge Error] Ошибка чтения {target_file}: {e}")

        await asyncio.sleep(1)

    task_info["status"] = "timeout"
    raise TimeoutError(f"Превышено время ожидания ответа в {target_file} ({timeout_seconds}с)")

# --- ОБРАБОТЧИКИ OLLAMA (порт 11434) ---

async def handle_ollama_tags(request: web.Request):
    return web.json_response(get_local_ollama_models())

async def handle_ollama_chat(request: web.Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {"error": "Невалидный JSON"}

    # 1. Сохраняем запрос в debug/output/
    saved_path_str = save_request_json("api_chat", payload)
    filename = Path(saved_path_str).name

    # Регистрируем задачу в глобальном списке
    task_info = {
        "id": filename,
        "endpoint": "/api/chat",
        "status": "received",
        "preview": str(payload.get("messages", [{}])[-1].get("content", ""))[:80]
    }
    pending_tasks.append(task_info)

    # 2. Локальный режим: умная заглушка
    if debug_state["mode"] == "local":
        task_info["status"] = "auto_mocked"
        response_data = generate_smart_ollama_response(payload)
        return web.json_response(response_data)

    # 3. Режим моста: ждём файл из debug/input/<filename>
    try:
        response_data = await wait_for_input_response(filename, task_info)
        return web.json_response(response_data)
    except TimeoutError as te:
        return web.json_response({"error": str(te)}, status=504)

# --- ОБРАБОТЧИКИ COMFYUI (порт 8188) ---

async def handle_comfy_models(request: web.Request):
    return web.json_response(get_local_comfy_models())

async def handle_comfy_prompt(request: web.Request):
    """Queue a workflow and let bridge mode complete it asynchronously."""
    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"error": "Невалидный JSON"}, status=400)

    saved_path_str = save_request_json("comfy_prompt", payload)
    filename = Path(saved_path_str).name

    if debug_state["mode"] == "local":
        prompt_id = f"mock_{filename[:-5]}"
        COMFY_TASKS[prompt_id] = {"status": "local"}
    else:
        prompt_id = f"bridge_{filename[:-5]}"
        task_info = {
            "id": filename,
            "endpoint": "/prompt",
            "status": "waiting",
            "preview": "ComfyUI workflow; upload the request JSON to Kaggle",
        }
        pending_tasks.append(task_info)
        COMFY_TASKS[prompt_id] = {
            "status": "waiting",
            "filename": filename,
            "task_info": task_info,
        }

    return web.json_response({"prompt_id": prompt_id, "number": 1})

async def handle_comfy_history(request: web.Request):
    """Report a completed image after its JSON and image file arrive from Kaggle."""
    prompt_id = request.match_info.get("prompt_id", "default")
    task = COMFY_TASKS.get(prompt_id)
    if task is None:
        return web.json_response({})

    if task["status"] == "local":
        image = {"filename": "in_prog.png", "subfolder": "", "type": "output"}
        status = {"status_str": "success", "completed": True}
    elif task["status"] == "error":
        return web.json_response({
            prompt_id: {
                "status": {
                    "status_str": "error",
                    "completed": True,
                    "messages": task["error"],
                },
                "outputs": {},
            }
        })
    elif task["status"] == "completed":
        image = {"filename": task["image_filename"], "subfolder": "", "type": "output"}
        status = {"status_str": "success", "completed": True}
    else:
        response_path = INPUT_DIR / task["filename"]
        if not response_path.is_file():
            return web.json_response({
                prompt_id: {
                    "status": {"status_str": "running", "completed": False},
                    "outputs": {},
                }
            })

        try:
            await asyncio.sleep(0.1)
            with response_path.open("r", encoding="utf-8") as response_file:
                response_data = json.load(response_file)
            if not isinstance(response_data, dict):
                raise ValueError("Ответ Kaggle должен быть JSON-объектом.")
            if response_data.get("status") == "error":
                task["status"] = "error"
                task["error"] = str(response_data.get("error", "Kaggle ComfyUI generation failed"))
                task["task_info"]["status"] = "failed"
                return await handle_comfy_history(request)

            image_filename = response_data.get("image_filename")
            if (
                not isinstance(image_filename, str)
                or Path(image_filename).name != image_filename
                or Path(image_filename).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}
            ):
                raise ValueError("Ответ Kaggle не содержит безопасное имя image_filename.")
            image_path = INPUT_DIR / image_filename
            if not image_path.is_file():
                return web.json_response({
                    prompt_id: {
                        "status": {"status_str": "running", "completed": False},
                        "outputs": {},
                    }
                })

            task["status"] = "completed"
            task["image_filename"] = image_filename
            task["task_info"]["status"] = "completed"
            COMFY_IMAGES[image_filename] = image_path
            image = {"filename": image_filename, "subfolder": "", "type": "output"}
            status = {"status_str": "success", "completed": True}
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"[Bridge Error] Invalid ComfyUI response {response_path}: {exc}")
            return web.json_response({
                prompt_id: {
                    "status": {"status_str": "running", "completed": False},
                    "outputs": {},
                }
            })

    return web.json_response({
        prompt_id: {
            "status": status,
            "outputs": {"9": {"images": [image]}},
        }
    })

async def handle_comfy_view(request: web.Request):
    """Serve the actual image copied from Kaggle into debug/input."""
    filename = request.query.get("filename", "")
    image_path = COMFY_IMAGES.get(filename)
    if image_path is None and filename == "in_prog.png":
        image_path = Path("assets/img/adv/in_prog.png")
    if Path(filename).name != filename:
        return web.json_response({"error": "Изображение не найдено; загрузите его из Kaggle в debug/input."}, status=404)
    if image_path is None or not image_path.is_file():
        if filename == "in_prog.png":
            empty_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            return web.Response(body=empty_png, content_type="image/png")
        return web.json_response({"error": "Изображение не найдено; загрузите его из Kaggle в debug/input."}, status=404)

    content_type = "image/png"
    if image_path.suffix.lower() in {".jpg", ".jpeg"}:
        content_type = "image/jpeg"
    elif image_path.suffix.lower() == ".webp":
        content_type = "image/webp"
    return web.FileResponse(image_path, headers={"Content-Type": content_type})

# --- ЗАПУСК МОК-СЕРВЕРОВ ---

@app.on_startup
async def start_mock_servers():
    # 1. Сервер Ollama (11434)
    ollama_app = web.Application()
    ollama_app.router.add_get("/api/tags", handle_ollama_tags)
    ollama_app.router.add_post("/api/chat", handle_ollama_chat)
    
    ollama_runner = web.AppRunner(ollama_app)
    await ollama_runner.setup()
    await web.TCPSite(ollama_runner, "localhost", 11434).start()
    print("=== [Mock Server] Запущен на порту 11434 (Ollama) ===")

    # 2. Сервер ComfyUI (8188)
    comfy_app = web.Application()
    comfy_app.router.add_get("/models/checkpoints", handle_comfy_models)
    comfy_app.router.add_post("/prompt", handle_comfy_prompt)
    comfy_app.router.add_get("/history/{prompt_id}", handle_comfy_history)
    comfy_app.router.add_get("/view", handle_comfy_view)
    
    comfy_runner = web.AppRunner(comfy_app)
    await comfy_runner.setup()
    await web.TCPSite(comfy_runner, "localhost", 8188).start()
    print("=== [Mock Server] Запущен на порту 8188 (ComfyUI) ===")

# Инициализируем UI
setup_debug_page()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="RPG Bot Debug Panel", host="127.0.0.1", port=DEBUG_PORT, reload=False, dark=True)