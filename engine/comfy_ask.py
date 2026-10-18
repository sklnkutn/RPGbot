import time
import random
import aiohttp
import asyncio
from pathlib import Path
from services.server_request import get_server_url
from services.loaders import _load_workflow_template, _download_comfy_image

OUTPUTS_DIR = Path("outputs")

async def generate_comfy_image(session_id: int, comfy_model: str, positive_prompt: str, timeout_seconds: int = 120) -> str | None:
    """
    Модифицирует шаблон workflow, отправляет в ComfyUI, ожидает генерации,
    скачивает готовый файл в outputs/ и возвращает веб-путь к нему.
    """
    try:
        # 1. Загружаем и модифицируем workflow
        workflow = _load_workflow_template()

        # Нода 4: Чекпоинт модели
        if "4" in workflow and "ckpt_name" in workflow["4"].get("inputs", {}):
            workflow["4"]["inputs"]["ckpt_name"] = comfy_model

        # Нода 6: Позитивный промпт
        if "6" in workflow and "text" in workflow["6"].get("inputs", {}):
            workflow["6"]["inputs"]["text"] = positive_prompt

        # Нода 3: Случайный сид
        if "3" in workflow and "seed" in workflow["3"].get("inputs", {}):
            workflow["3"]["inputs"]["seed"] = random.randint(1, 10**15)

        # Нода 9: Префикс имени
        if "9" in workflow and "filename_prefix" in workflow["9"].get("inputs", {}):
            workflow["9"]["inputs"]["filename_prefix"] = f"RPG_s{session_id}"

        # 2. Отправляем запрос на генерацию в ComfyUI
        prompt_url = get_server_url("comfy", "prompt")
        payload = {"prompt": workflow}

        post_timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=post_timeout) as session:
            async with session.post(prompt_url, json=payload) as resp:
                if resp.status != 200:
                    text_err = await resp.text()
                    print(f"[ComfyUI Error] Не удалось поставить задачу в очередь: {text_err}")
                    return None
                data = await resp.json()
                prompt_id = data.get("prompt_id")

        if not prompt_id:
            print("[ComfyUI Error] Сервер не вернул prompt_id.")
            return None

        # 3. Ожидание завершения генерации (Polling очереди /history)
        history_url = get_server_url("comfy", f"history/{prompt_id}")
        start_time = time.time()
        image_info = None

        while time.time() - start_time < timeout_seconds:
            await asyncio.sleep(2)
            try:
                poll_timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=poll_timeout) as session:
                    async with session.get(history_url) as resp:
                        if resp.status == 200:
                            history_data = await resp.json()
                            if prompt_id in history_data:
                                outputs = history_data[prompt_id].get("outputs", {})
                                # Ищем ноду 9 (SaveImage) в outputs
                                if "9" in outputs and "images" in outputs["9"]:
                                    images = outputs["9"]["images"]
                                    if images:
                                        image_info = images[0]
                                        break
            except Exception:
                pass  # Временные сетевые сбои при опросе не прерывают цикл

        if not image_info:
            print(f"[ComfyUI Timeout] Превышено время ожидания ({timeout_seconds}с) генерации кадра.")
            return None

        # 4. Скачивание изображения в локальную папку проекта
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        unique_filename = f"session_{session_id}_{int(time.time())}.png"
        target_file_path = OUTPUTS_DIR / unique_filename

        success = await _download_comfy_image(
            filename=image_info["filename"],
            subfolder=image_info.get("subfolder", ""),
            folder_type=image_info.get("type", "output"),
            target_path=target_file_path
        )

        if success:
            # Возвращаем путь, доступный для NiceGUI и веб-клиента
            return f"/outputs/{unique_filename}"

    except Exception as e:
        print(f"[ComfyUI Pipeline Error]: {e}")

    return None