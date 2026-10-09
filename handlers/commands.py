from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from services.llm import ask_llm
from db import save_message
from states import GameStates

router = Router() #Создание маршрутизатора для обработки команд

start_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Начать приключение", callback_data="start_story")],
    ]
)

#команда /start
@router.message(CommandStart()) #Декоратор, который будет реагировать на команду /start
async def start_handler(message: Message, state: FSMContext):
    await state.set_state(GameStates.START)
    welcome_text = (
        f"Привет, {message.from_user.full_name}!\n\n"
        "Добро пожаловать в нашего бота.\n"
        "Готов погрузиться в мир RPG и приключений?\n\n"
        "Выбери желаемые настройки и начни свое путешествие прямо сейчас!"
    )
    await message.answer(welcome_text, reply_markup=start_keyboard)

#Обработчик нажатия кнопки "Начать приключение"
@router.callback_query(lambda c: c.data == "start_story") #Декоратор, который будет реагировать на нажатие кнопки
async def start_story_handler(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.IN_PROGRESS) #Установка состояния игры в "в процессе"
    await callback_query.answer() #Подтверждение нажатия кнопки
    user_id = callback_query.from_user.id #Получение id пользователя
    start_prompt = "Заглушка" #Заглушка для стартового промпта, который будет использоваться в LLM
    await save_message(user_id=user_id, sender="user", text=start_prompt)
    llm_text = await ask_llm(start_prompt) #Отправка стартового промпта в LLM и получение ответа
    bot_response = await callback_query.message.answer(llm_text) #Отправка сообщения обратно пользователю
    await save_message(user_id=user_id, sender="bot", text=bot_response.text) #Сохранение ответа бота в базу данных

