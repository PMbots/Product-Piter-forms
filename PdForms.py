import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import logging
from database import (
    create_all_tables, create_connection, save_response_to_db,
    save_user_to_db, save_log, add_reminder, update_reminder,
    deactivate_reminder, delete_user_from_db
)

TEST_TOKEN = "6511297435:AAF0LWNmaaB3oBpYfWyUKB7n322soW45AmU"
API_TOKEN = '7645108253:AAHIjxssce32bn3DQKbI4tvuiYHvOWoOnco'

# Инициализация бота и диспетчера
bot = Bot(token=TEST_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создание базы данных при запуске
create_all_tables()

# Состояния для опроса
class SurveyStates(StatesGroup):
    NAME = State()
    COMPANY = State()
    EXPERIENCE = State()
    OTHER_EXPERIENCE = State()
    INDUSTRY = State()
    OTHER_INDUSTRY = State()
    LOCATION = State()
    POSITION = State()

# Временная функция для напоминания
async def reminder_task(telegram_user_id, chat_id):
    await asyncio.sleep(30 * 60)  # Ожидание 30 минут
    conn = create_connection('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT UserID FROM Users WHERE TelegramUserID = ?", (telegram_user_id,))
    user = cursor.fetchone()
    if user:
        user_id = user[0]
        await bot.send_message(chat_id, "Напоминаем о начале опроса! Не забудь нажать кнопку 'Начать'.")
        save_log(
            user_id=telegram_user_id,
            event="Напоминание отправлено",
            timestamp=datetime.now().isoformat()
        )
        update_reminder(user_id, "FirstReminderSent", datetime.now().isoformat())
        asyncio.create_task(delete_user_task(telegram_user_id, chat_id))
    conn.close()

# Временная функция для удаления пользователя
async def delete_user_task(telegram_user_id, chat_id):
    await asyncio.sleep(40 * 60)  # Ожидание 40 минут
    delete_user_from_db(telegram_user_id)
    await bot.send_message(chat_id, "Мы удалили твои данные из системы из-за неактивности.")
    save_log(
        user_id=telegram_user_id,
        event="Пользователь удален из базы данных за неактивность",
        timestamp=datetime.now().isoformat()
    )
    conn = create_connection('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT UserID FROM Users WHERE TelegramUserID = ?", (telegram_user_id,))
    user = cursor.fetchone()
    if user:
        user_id = user[0]
        deactivate_reminder(user_id)
    conn.close()

# Приветственное сообщение и начало опроса
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Начать"))
    save_user_to_db(
        telegram_user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    save_log(
        user_id=message.from_user.id,
        event="Команда /start выполнена",
        timestamp=datetime.now().isoformat()
    )
    conn = create_connection('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT UserID FROM Users WHERE TelegramUserID = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if user:
        user_id = user[0]
        add_reminder(user_id)
    conn.close()
    await message.answer(
        "Привет! Это бот твоего комьюнити Продакты СПБ. Нажми 'Начать', чтобы пройти опрос.",
        reply_markup=markup
    )
    asyncio.create_task(reminder_task(message.from_user.id, message.chat.id))

@dp.message_handler(lambda message: message.text == "Начать")
async def start_survey(message: types.Message):
    save_log(
        user_id=message.from_user.id,
        event="Опрос начат",
        timestamp=datetime.now().isoformat()
    )
    conn = create_connection('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT UserID FROM Users WHERE TelegramUserID = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if user:
        user_id = user[0]
        deactivate_reminder(user_id)
    conn.close()
    await message.answer("Как тебя зовут? Напиши в формате: Имя и Фамилия.", reply_markup=ReplyKeyboardRemove())
    await SurveyStates.NAME.set()

@dp.message_handler(state=SurveyStates.NAME)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    save_response_to_db(
        telegram_user_id=message.from_user.id,
        question="Как тебя зовут?",
        answer=message.text
    )
    save_log(
        user_id=message.from_user.id,
        event="Ответ на вопрос: Как тебя зовут?",
        timestamp=datetime.now().isoformat()
    )
    await message.answer("Где ты работаешь? Укажи название компании.")
    await SurveyStates.COMPANY.set()

@dp.message_handler(state=SurveyStates.COMPANY)
async def get_company(message: types.Message, state: FSMContext):
    await state.update_data(company=message.text)
    save_response_to_db(
        telegram_user_id=message.from_user.id,
        question="Где ты работаешь?",
        answer=message.text
    )
    save_log(
        user_id=message.from_user.id,
        event="Ответ на вопрос: Где ты работаешь?",
        timestamp=datetime.now().isoformat()
    )
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Менее 1 года", "1-3 года", "3-5 лет", "Более 5 лет", "Другое")
    await message.answer("Какой у тебя опыт в продакт-менеджменте?", reply_markup=markup)
    await SurveyStates.EXPERIENCE.set()

@dp.message_handler(state=SurveyStates.EXPERIENCE)
async def get_experience(message: types.Message, state: FSMContext):
    if message.text == "Другое":
        save_response_to_db(
            telegram_user_id=message.from_user.id,
            question="Какой у тебя опыт в продакт-менеджменте?",
            answer=message.text,
            is_other_option=True
        )
        save_log(
            user_id=message.from_user.id,
            event="Ответ: Другое в опыте работы",
            timestamp=datetime.now().isoformat()
        )
        await message.answer("Пожалуйста, укажи свой опыт текстом.", reply_markup=ReplyKeyboardRemove())
        await SurveyStates.OTHER_EXPERIENCE.set()
    else:
        save_response_to_db(
            telegram_user_id=message.from_user.id,
            question="Какой у тебя опыт в продакт-менеджменте?",
            answer=message.text
        )
        save_log(
            user_id=message.from_user.id,
            event=f"Ответ на опыт: {message.text}",
            timestamp=datetime.now().isoformat()
        )
        await ask_industry(message, state)

@dp.message_handler(state=SurveyStates.OTHER_EXPERIENCE)
async def get_other_experience(message: types.Message, state: FSMContext):
    await state.update_data(experience=message.text)
    save_response_to_db(
        telegram_user_id=message.from_user.id,
        question="Укажи свой опыт текстом.",
        answer=message.text
    )
    save_log(
        user_id=message.from_user.id,
        event=f"Ответ на 'Другой опыт': {message.text}",
        timestamp=datetime.now().isoformat()
    )
    await ask_industry(message, state)

async def ask_industry(message: types.Message, state: FSMContext):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("IT/Tech", "FinTech", "eCommerce", "Маркетинг", "Геймдев", "Другое")
    await message.answer("В какой сфере ты работаешь?", reply_markup=markup)
    await SurveyStates.INDUSTRY.set()

@dp.message_handler(state=SurveyStates.INDUSTRY)
async def get_industry(message: types.Message, state: FSMContext):
    if message.text == "Другое":
        save_response_to_db(
            telegram_user_id=message.from_user.id,
            question="В какой сфере ты работаешь?",
            answer=message.text,
            is_other_option=True
        )
        save_log(
            user_id=message.from_user.id,
            event="Ответ: Другая сфера работы",
            timestamp=datetime.now().isoformat()
        )
        await message.answer("Пожалуйста, укажи сферу работы текстом.", reply_markup=ReplyKeyboardRemove())
        await SurveyStates.OTHER_INDUSTRY.set()
    else:
        save_response_to_db(
            telegram_user_id=message.from_user.id,
            question="В какой сфере ты работаешь?",
            answer=message.text
        )
        save_log(
            user_id=message.from_user.id,
            event=f"Ответ на сферу работы: {message.text}",
            timestamp=datetime.now().isoformat()
        )
        await ask_location(message, state)

@dp.message_handler(state=SurveyStates.OTHER_INDUSTRY)
async def get_other_industry(message: types.Message, state: FSMContext):
    await state.update_data(industry=message.text)
    save_response_to_db(
        telegram_user_id=message.from_user.id,
        question="Укажи сферу работы текстом.",
        answer=message.text
    )
    save_log(
        user_id=message.from_user.id,
        event=f"Ответ: Другая сфера работы - {message.text}",
        timestamp=datetime.now().isoformat()
    )
    await ask_location(message, state)

async def ask_location(message: types.Message, state: FSMContext):
    await message.answer("В какой стране и городе ты живешь?", reply_markup=ReplyKeyboardRemove())
    await SurveyStates.LOCATION.set()

@dp.message_handler(state=SurveyStates.LOCATION)
async def get_location(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text)
    save_response_to_db(
        telegram_user_id=message.from_user.id,
        question="В какой стране и городе ты живешь?",
        answer=message.text
    )
    save_log(
        user_id=message.from_user.id,
        event=f"Ответ на местоположение: {message.text}",
        timestamp=datetime.now().isoformat()
    )
    await message.answer(
        "На какой позиции ты работаешь? Как ты можешь описать свою основную деятельность? "
        "Чем занимаешься, что создаешь, за какие процессы отвечаешь?",
        reply_markup=ReplyKeyboardRemove()
    )
    await SurveyStates.POSITION.set()

@dp.message_handler(state=SurveyStates.POSITION)
async def get_position(message: types.Message, state: FSMContext):
    await state.update_data(position=message.text)
    save_response_to_db(
        telegram_user_id=message.from_user.id,
        question="На какой позиции ты работаешь?",
        answer=message.text
    )
    save_log(
        user_id=message.from_user.id,
        event=f"Опрос завершен. Ответ на позицию: {message.text}",
        timestamp=datetime.now().isoformat()
    )
    await message.answer("Спасибо за участие в опросе! Мы свяжемся с тобой в ближайшее время для обсуждения.")
    logging.info(f"Ответы пользователя: {await state.get_data()}")
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
