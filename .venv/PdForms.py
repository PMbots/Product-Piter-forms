from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import logging

API_TOKEN = '7645108253:AAHIjxssce32bn3DQKbI4tvuiYHvOWoOnco'

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

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

# Приветственное сообщение и начало опроса
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Начать"))
    await message.answer(
        "Привет! Это бот твоего комьюнити Продакты СПБ....",  # Начало приветственного сообщения
        reply_markup=markup
    )
    reply_markup=ReplyKeyboardRemove()

@dp.message_handler(lambda message: message.text == "Начать")
async def start_survey(message: types.Message):
    await message.answer("Как тебя зовут? Напиши в формате: Имя и Фамилия.")
    await SurveyStates.NAME.set()

# Вопросы поочередно
@dp.message_handler(state=SurveyStates.NAME)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Где ты работаешь? Укажи название компании.", reply_markup=ReplyKeyboardRemove())
    await SurveyStates.COMPANY.set()

@dp.message_handler(state=SurveyStates.COMPANY)
async def get_company(message: types.Message, state: FSMContext):
    await state.update_data(company=message.text)
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Менее 1 года", "1-3 года", "3-5 лет", "Более 5 лет", "Другое")
    await message.answer("Какой у тебя опыт в продакт-менеджменте?", reply_markup=markup)
    await SurveyStates.EXPERIENCE.set()

@dp.message_handler(state=SurveyStates.EXPERIENCE)
async def get_experience(message: types.Message, state: FSMContext):
    if message.text == "Другое":
        await message.answer("Пожалуйста, укажи свой опыт текстом.", reply_markup=ReplyKeyboardRemove())
        await SurveyStates.OTHER_EXPERIENCE.set()
    else:
        await state.update_data(experience=message.text)
        await ask_industry(message, state)

@dp.message_handler(state=SurveyStates.OTHER_EXPERIENCE)
async def get_other_experience(message: types.Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await ask_industry(message, state)

async def ask_industry(message: types.Message, state: FSMContext):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("IT/Tech", "FinTech", "eCommerce", "Маркетинг", "Геймдев", "Другое")
    await message.answer("В какой сфере ты работаешь?", reply_markup=markup)
    await SurveyStates.INDUSTRY.set()

@dp.message_handler(state=SurveyStates.INDUSTRY)
async def get_industry(message: types.Message, state: FSMContext):
    if message.text == "Другое":
        await message.answer("Пожалуйста, укажи сферу работы текстом.", reply_markup=ReplyKeyboardRemove())
        await SurveyStates.OTHER_INDUSTRY.set()
    else:
        await state.update_data(industry=message.text)
        await ask_location(message, state)

@dp.message_handler(state=SurveyStates.OTHER_INDUSTRY)
async def get_other_industry(message: types.Message, state: FSMContext):
    await state.update_data(industry=message.text)
    await ask_location(message, state)

async def ask_location(message: types.Message, state: FSMContext):
    await message.answer("В какой стране и городе ты живешь?", reply_markup=ReplyKeyboardRemove())
    await SurveyStates.LOCATION.set()

@dp.message_handler(state=SurveyStates.LOCATION)
async def get_location(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text)
    await message.answer(
        "На какой позиции ты работаешь? Как ты можешь описать свою основную деятельность? "
        "Чем занимаешься, что создаешь, за какие процессы отвечаешь?",
        reply_markup=ReplyKeyboardRemove()
    )
    await SurveyStates.POSITION.set()

@dp.message_handler(state=SurveyStates.POSITION)
async def get_position(message: types.Message, state: FSMContext):
    await state.update_data(position=message.text)
    data = await state.get_data()
    await message.answer("Спасибо за участие в опросе! Мы свяжемся с тобой в ближайшее время для обсуждения.")
    logging.info(f"Ответы пользователя: {data}")
    await state.finish()

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
