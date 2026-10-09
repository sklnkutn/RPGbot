import asyncio
from aiohttp import web

async def handle_chat(request: web.Request) -> web.Response:
    """Обработчик эндпоинта /api/chat — симуляция работы Ollama."""
    data = await request.json()  # Получаем JSON данные из запроса
    message = data.get("messages", [])
    user_message = message[-1]["content"] if message else "Пользователь не ввел текст."
    print(f"[Mock Ollama] Получено сообщение от пользователя: {user_message}")

    await asyncio.sleep(3)  # Симуляция задержки ответа

    response_payload = {
        "model": data.get("model", "mock-model"),
        "message": {
            "role": "assistant",
            "content": f"[Mock Ollama]:Ответ на сообщение: {user_message}"
        },
        "done" : True
    }

    print("[MOCK OLLAMA] Отправка ответа боту...")
    return web.json_response(response_payload)

def main():
    app = web.Application()
    app.router.add_post("/api/chat", handle_chat)  # Регистрируем обработчик для POST-запросов на /api/chat
    print("=== ЗАПУСК МОК-СЕРВЕРА OLLAMA (http://localhost:11434) ===")
    web.run_app(app, host="localhost", port=11434)  # Запуск веб-сервера на localhost:11434

if __name__ == "__main__":
    main()
