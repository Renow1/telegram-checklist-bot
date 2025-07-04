
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup

from config import TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

CHECKLIST_ITEMS = [
    "Поверхности протерты от масла",
    "Ёмкости протерты от масла",
    "Антисептик долит",
    "Масла долиты",
    "Простынь перестелена",
    "Подголовник перестелен",
    "Мусор выкинут",
    "Дверь и ручка протерты от масла с обеих сторон",
    "Обогреватель выключен",
    "Чистые полотенца доложены",
]

class Form(StatesGroup):
    surname = State()
    room = State()
    studio = State()
    date = State()
    battery = State()
    checklist = State()
    confirm = State()

def generate_checklist_markup(checked_items):
    markup = InlineKeyboardMarkup(row_width=1)
    for i, item in enumerate(CHECKLIST_ITEMS):
        checked = "✅" if i in checked_items else "⬜️"
        markup.add(InlineKeyboardButton(f"{checked} {item}", callback_data=f"toggle_{i}"))
    if len(checked_items) == len(CHECKLIST_ITEMS):
        markup.add(InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_checklist"))
    return markup

@dp.message_handler(commands='start')
async def start_cmd(message: types.Message):
    await message.reply("Введите вашу фамилию:")
    await Form.surname.set()

@dp.message_handler(state=Form.surname)
async def process_surname(message: types.Message, state: FSMContext):
    await state.update_data(surname=message.text)
    await message.reply("Введите номер кабинета:")
    await Form.room.set()

@dp.message_handler(state=Form.room)
async def process_room(message: types.Message, state: FSMContext):
    await state.update_data(room=message.text)
    await message.reply("Введите название студии:")
    await Form.studio.set()

@dp.message_handler(state=Form.studio)
async def process_studio(message: types.Message, state: FSMContext):
    await state.update_data(studio=message.text)
    await message.reply("Введите дату (например, 03.07.2025):")
    await Form.date.set()

@dp.message_handler(state=Form.date)
async def process_date(message: types.Message, state: FSMContext):
    await state.update_data(date=message.text)
    await message.reply("Введите заряд телефона (в процентах):")
    await Form.battery.set()

@dp.message_handler(state=Form.battery)
async def process_battery(message: types.Message, state: FSMContext):
    await state.update_data(battery=message.text)
    await state.update_data(checked=[])
    markup = generate_checklist_markup([])
    await message.answer("Пройдите чек-лист, нажимая на пункты:", reply_markup=markup)
    await Form.checklist.set()

@dp.callback_query_handler(lambda c: c.data.startswith('toggle_'), state=Form.checklist)
async def toggle_checklist_item(callback_query: types.CallbackQuery, state: FSMContext):
    index = int(callback_query.data.split("_")[1])
    data = await state.get_data()
    checked = data.get("checked", [])
    if index in checked:
        checked.remove(index)
    else:
        checked.append(index)
    await state.update_data(checked=checked)
    markup = generate_checklist_markup(checked)
    await callback_query.message.edit_reply_markup(markup)
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == "confirm_checklist", state=Form.checklist)
async def confirm_checklist(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    checked = data.get("checked", [])
    checklist_text = "\n".join(
        f"[{'✅' if i in checked else '❌'}] {item}" for i, item in enumerate(CHECKLIST_ITEMS)
    )
    await state.update_data(checklist=checklist_text)
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("✅ Подтвердить"))
    await callback_query.message.answer("Нажмите 'Подтвердить' для сохранения результатов.", reply_markup=markup)
    await Form.confirm.set()
    await callback_query.answer()

@dp.message_handler(lambda message: message.text == "✅ Подтвердить", state=Form.confirm)
async def process_confirm(message: types.Message, state: FSMContext):
    data = await state.get_data()
    report = (
        f"Фамилия: {data['surname']}\n"
        f"Кабинет: {data['room']}\n"
        f"Студия: {data['studio']}\n"
        f"Дата: {data['date']}\n"
        f"Заряд телефона: {data['battery']}%\n\n"
        f"Чек-лист:\n{data['checklist']}\n"
    )
    os.makedirs("data/submissions", exist_ok=True)
    filename = f"data/submissions/{data['surname']}_{data['date'].replace('.', '-')}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    await message.reply("✅ Данные сохранены. Спасибо!", reply_markup=types.ReplyKeyboardRemove())
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
