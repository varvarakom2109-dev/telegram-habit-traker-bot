import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timedelta
import sqlite3
from math import ceil

MAX_HABITS = 12
PAGE_SIZE = 3

from keyboards import main_menu
from states import AddHabit, EditHabit
from datebase import (
    create_tables,
    add_habit,
    get_user_habits_full,
    delete_habit,
    log_habit,
    update_habit_time,
    update_habit_title,
    clear_history,
    get_habit_history,
    get_habit_stats,
    get_habit_history,
    was_reminder_send,
    get_connection,
    delete_habit_by_id
)
from config import TOKEN, ADMIN_ID

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_habit_streak(user_id: int, habit_title: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT date FROM habits_logs WHERE user_id = ? AND habit_title = ? AND status = 'done' ORDER BY date DESC",
        (user_id, habit_title)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return 0
    
    streak = 0
    today = datetime.now().date()
    day_counter = today
    
    for (date_str,) in rows:
        log_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if log_date == day_counter:
            streak += 1
            day_counter -= timedelta(days=1)
        elif log_date < day_counter:
            break
        
    return streak

async def show_habits_page(target: types.Message, user_id: int, page: int, edit: bool = False):
    habits = get_user_habits_full(user_id)
    
    if not habits:
        if hasattr(target, "edit_text"):
            await target.edit_text("У тебя пока нет привычек.")
        else:
            await target.answer("У тебя пока нет привычек.")
        return
    
    total_pages = ceil(len(habits) / PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    current = habits[start:end]
    
    text = f"({page + 1} / {total_pages}) Выбери привычку:\n\n"
    keyboard = []
    
    for habit_id, title, time in current:
        text += f"- {title} ({time})\n"
        keyboard.append([
            InlineKeyboardButton(text=f"{title} - {time}\n", callback_data=f"edit:{habit_id}")
        ])
        
    keyboard.append([
        InlineKeyboardButton(text="<-", callback_data=f"page:{page - 1}"),
        InlineKeyboardButton(text="->", callback_data=f"page:{page + 1}")
    ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    if edit:
        await target.edit_text(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)
        
async def send_reminder(bot):
    while True:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, title, time FROM habits")
        all_habits = cursor.fetchall()
        conn.close()
        
        now = datetime.now().strftime("%H:%M")
        today = datetime.now().strftime("%Y-%m-%d")

        for user_id, title, habit_time in all_habits:
            if habit_time[:5] == now:
                if was_reminder_send(user_id, title, today):
                    continue
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                       [
                           InlineKeyboardButton(text="Выполнил", callback_data=f"done:{title}"),
                           InlineKeyboardButton(text="Не выполнил", callback_data=f"miss:{title}")
                       ]
                   ])
                
                try:
                    await bot.send_message( user_id, f"Напоминание: {title}",
                       reply_markup=keyboard
                   )                 
                except Exception as e:
                    print(f"Ошибка при отправке пользователю {user_id}: {e}")
        await asyncio.sleep(60) 

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
          "Привет!\n"
        "Я - бот трекинга привычек."
        "Выберите действие:",
        reply_markup=main_menu()
    )
    
@dp.message(lambda m: m.text == "Добавить привычку")
@dp.message(Command("add"))
async def add_habit_start(message: types.Message, state: FSMContext):
    await message.answer("Напиши название привычки")
    await state.set_state(AddHabit.waiting_for_title)

@dp.message(AddHabit.waiting_for_title)
async def add_habit_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    
    await message.answer(
        f"Привычка {message.text} добавлена!\n"
        "Теперь введи время напоминания.\n"
        "Формат: HH:MM (например 08:30)"
    )
    
    await state.set_state(AddHabit.waiting_for_time)
    
@dp.message(AddHabit.waiting_for_time)
async def add_habit_time(message: types.Message, state: FSMContext):
    try:
        habit_time = datetime.strptime(message.text, "%H:%M").time()
    except ValueError:
        await message.answer("Неверный формат времени, попробуй ещё раз (HH:MM)")
        return
    
    await state.update_data(time=str(habit_time))
    data = await state.get_data()
    
    habits = get_user_habits_full(message.from_user.id)
    
    if len(habits) >= MAX_HABITS:
        await message.answer(f"Можно создать только {MAX_HABITS} привычек!\nУдалите одну из существующих.")
        await state.clear()
        return
    
    add_habit(
    user_id=message.from_user.id,
    title=data["title"],
    time=data["time"]
)
    await message.answer(
        f"Привычка сохранена!\n"
        f"Название: {data['title']}\n"
        f"Время: {data['time']}"
    )
    
    await state.clear()
    
@dp.message(lambda m: m.text == "Мои привычки")
@dp.message(Command("habits"))
async def show_habits(message: types.Message):
    habits = get_user_habits_full(message.from_user.id)
    if not habits:
        await message.answer("У тебя пока нет привычек.")
        return

    text = "Твои привычки:\n"
    for i, (habit_id, title, time) in enumerate(habits, start=1):
        streak = get_habit_streak(message.from_user.id, title)
        text += f"{i}. {title} - {time} | 🔥{streak} \n"
    await message.answer(text)
    
    
@dp.message(F.text == "Редактировать привычки")
@dp.message(Command("edit"))
async def edit_habits(message: types.Message):
    await show_habits_page(message, message.from_user.id, page=0, edit=False)
    
@dp.message(lambda m: m.text == "Отмена")
async def cancel_edit(message: types.Message):
    await show_habits_page(message, message.from_user.id, page=0, edit=True)
    
@dp.callback_query(lambda c: c.data.startswith("page:"))
async def change_page(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    await show_habits_page(callback.message, user_id, page=page, edit=True)
    await callback.answer()
    
@dp.callback_query(lambda c: c.data.startswith("edit:"))
async def edit_habit_menu(callback: types.CallbackQuery, state: FSMContext):
    habit_id = int(callback.data.split(":")[1])
    await state.update_data(habit_id=habit_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить название", callback_data=f"edit_title:{habit_id}")],
        [InlineKeyboardButton(text="Изменить время", callback_data=f"edit_time:{habit_id}")],
        [InlineKeyboardButton(text="Удалить", callback_data=f"delete_id:{habit_id}")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
    ])
    await callback.message.edit_text("Что сделать с привычкой?", reply_markup=keyboard)
    await callback.answer()
    
@dp.callback_query(lambda c: c.data.startswith("edit_title:"))
async def edit_title_start(callback: types.CallbackQuery, state: FSMContext):
    habit_id = int(callback.data.split(":")[1])
    await state.update_data(habit_id=habit_id)
    await callback.message.edit_text("Введи новое название привычки:")
    await state.set_state(EditHabit.waiting_for_new_title)
    await callback.answer()


@dp.message(EditHabit.waiting_for_new_title)
async def save_new_title(message: types.Message, state: FSMContext):
    data = await state.get_data()
    habit_id = data["habit_id"]
    update_habit_title(habit_id, message.text)
    await message.answer("Название привычки обновлено!")
    await state.clear()
    
@dp.callback_query(lambda c: c.data.startswith("edit_time:"))
async def edit_time_start(callback: types.CallbackQuery, state: FSMContext):
    habit_id = int(callback.data.split(":")[1])
    await state.update_data(habit_id=habit_id)
    await callback.message.edit_text("Введи новое время (HH:MM):")
    await state.set_state(EditHabit.waiting_for_new_time)
    await callback.answer()


@dp.message(EditHabit.waiting_for_new_time)
async def save_new_time(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%H:%M")
    except ValueError:
        await message.answer("Неверный формат! Используй HH:MM")
        return
    
    data = await state.get_data()
    habit_id = data["habit_id"]
    update_habit_time(habit_id, message.text)
    await message.answer("Время привычки обновлено!")
    await state.clear()
    
@dp.callback_query(lambda c: c.data.startswith("delete_id:"))
async def delete_habit_by_id_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    habit_id = data.get("habit_id")
    if habit_id:
        delete_habit_by_id(habit_id)
    await callback.message.edit_text("Привычка удалена!")
    await state.clear()
    await callback.answer()
    
@dp.callback_query(lambda c: c.data == "cancel")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Действие отменено!")
    await callback.answer()
    
@dp.message(lambda m: m.text == "Статистика")
@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    done, missed, percent = get_habit_stats(message.from_user.id)
    await message.answer(f"Статистика привычек:\n\nВыполнено: {done}\nПропущено: {missed}\nПроцент выполнения: {percent}%")
    
@dp.message(lambda m: m.text == "История")
@dp.message(Command("history"))
async def history(message: types.Message):
    history_data = get_habit_history(message.from_user.id, 7)
    if not history_data:
        await message.answer("История за последние 7 дней пустая.")
        return

    text = "История привычек (последние 7 дней):\n"
    for habit, date, status in history_data:
        emoji = "✅" if status == "done" else "❌"
        text += f"{date}: {habit} {emoji}\n"
    await message.answer(text)
    
@dp.message(lambda m: m.text == "Очистить историю")
@dp.message(Command("clear_history"))
async def clear_history_cmd(message: types.Message):
    clear_history(message.from_user.id)
    await message.answer("История привычек полностью очищена.")
    
@dp.callback_query(F.data.startswith("done:"))
@dp.message(Command("done"))
async def habit_done(callback: types.CallbackQuery):
    title = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    today = datetime.now().strftime("%Y-%m-%d")
    
    log_habit(user_id, title, "done")
    
    await callback.message.edit_text(f"Привычка ({title}) выполнена!")
    await callback.answer()
    
@dp.callback_query(F.data.startswith("miss:"))
@dp.message(Command("miss"))
async def habit_miss(callback: types.CallbackQuery):
    title = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    today = datetime.now().strftime("%Y-%m-%d")
    
    log_habit(user_id, title, "missed")
    
    await callback.message.edit_text(f"Привычка ({title}) не выполнена.")
    await callback.answer()
    
async def main():
    create_tables()
    asyncio.create_task(send_reminder(bot))
    await dp.start_polling(bot)
    
if __name__ == "__main__":
    asyncio.run(main())