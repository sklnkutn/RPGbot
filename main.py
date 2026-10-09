import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from dotenv import load_dotenv
from states import GameStates

from db import init_db, save_message
from services.llm import ask_llm
from handlers.commands import router as commands_router

load_dotenv() #Загрузка переменных окружения из файла .env

TOKEN = os.getenv("BOT_TOKEN") #Чтение токена из переменных окружения

raw_users = os.getenv("ALLOWED_USERS","") #Чтение списка разрешенных пользователей из переменных окружения
ALLOWED_USERS = {
    int(cleaned_user)
    for user_id in raw_users.split(",")
    if (cleaned_user := user_id.strip()).isdigit()
} #Нормализация списка разрешенных пользователей

bot = Bot(token=TOKEN) #Присвоение токена боту
dp = Dispatcher() #Создание диспетчера для обработки сообщений

dp.include_router(router=commands_router) #Подключение маршрутизатора команд к диспетчеру

@dp.message(GameStates.IN_PROGRESS, F.from_user.id.in_(ALLOWED_USERS)) #Декоратор, который будет реагировать на сообщения
async def game_dialog_handler(message: types.Message): #Функция, которая будет отвечать на сообщения
    user_id = message.from_user.id #Получение id пользователя
    user_text = message.text or "Пользователь не ввел текст." #Получение текста сообщения
    await save_message(user_id=user_id, sender="user", text=user_text) #Сохранение сообщения в базу данных
    #Новая часть кода, которая будет отправлять сообщение в LLM
    llm_text = await ask_llm(user_text) #Отправка сообщения в LLM и получение ответа
    bot_response = await message.answer(llm_text) #Отправка сообщения обратно пользователю
    await save_message(user_id=user_id, sender="bot", text=bot_response.text) #Сохранение ответа бота в базу данных

async def main(): #Функция, которая будет запускать бота
    await init_db() #Инициализация базы данных
    print("База данных инициализирована.Бот готов к работе.") #Вывод сообщения в консоль
    await dp.start_polling(bot) #Запуск бота
if __name__ == "__main__": #Проверка, что файл запущен напрямую
    asyncio.run(main()) #Запуск функции main