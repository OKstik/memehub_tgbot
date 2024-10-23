from datetime import datetime
import csv
import os

from aiogram.types import FSInputFile
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Video, InlineQuery, InlineQueryResultCachedVideo, InlineKeyboardMarkup, \
    InlineKeyboardButton, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.dispatcher.middlewares.base import BaseMiddleware
import logging
import sqlite3
import asyncio

API_TOKEN = '7117454247:AAHpIN4gbPdO2M8mKkbmCg1vfJqdi-SRFpk'

logging.basicConfig(level=logging.INFO)

bot = Bot(API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# Подключение к базе данных SQLite
conn = sqlite3.connect('videos.db')
cursor = conn.cursor()

# Создание таблицы, если ее нет
cursor.execute('''
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY,
    file_id TEXT NOT NULL,
    description TEXT NOT NULL,
    usage_count INTEGER DEFAULT 0   
)
''')
conn.commit()

# Создание таблицы для администраторов
cursor.execute('''
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY,
    username TEXT
)
''')
conn.commit()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    last_used TIMESTAMP,
    inline_query_count INTEGER DEFAULT 1
)
''')
conn.commit()


# Определение состояний
class VideoState(StatesGroup):
    awaiting_video = State()
    awaiting_description = State()
    awaiting_update_id = State()
    awaiting_new_description = State()
    awaiting_delete_id = State()
    awaiting_admin_id = State()
    awaiting_del_admin_id = State()


# Функция для проверки, является ли пользователь администратором
def is_admin(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM admins WHERE id = ?", (user_id,))
    return cursor.fetchone() is not None


# Middleware для проверки прав доступа
class AdminOnlyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Проверяем, является ли событие сообщением
        if isinstance(event, Message):
            # Проверяем, является ли сообщение текстовым
            if event.content_type == 'text':
                if event.text.startswith("/start"):
                    # Разрешаем команду /start для всех пользователей
                    return await handler(event, data)
                if not is_admin(event.from_user.id):
                    await event.answer("Извините, доступ к этой функции имеют только администраторы.")
                    return

        # Если событие не является сообщением или не текстовым, просто передаем управление дальше
        return await handler(event, data)


# Регистрация Middleware
dp.message.middleware(AdminOnlyMiddleware())


# Обработчики команд
@dp.message(Command('start'))
async def send_welcome(message: types.Message):
    await message.answer("Привет! Отправь /upload для загрузки видео.")

# Перезапуск ВПН на роутере, специально для Антона
@dp.message(Command('тумблер'))
async def send_welcome(message: types.Message):
    r = requests.post('http://62.133.60.64:51821/api/session', json={'password': 'SHo@K___'})
    cookies = r.cookies.get_dict()
    requests.post('http://62.133.60.64:51821/api/wireguard/client/ec75016c-7f6f-4a3c-bccf-b33791cf2aab/disable',
                  cookies=cookies)
    requests.post('http://62.133.60.64:51821/api/wireguard/client/ec75016c-7f6f-4a3c-bccf-b33791cf2aab/enable',
                  cookies=cookies)
    await message.answer('Как ты заебал! Перезапустил.')
    
# Обработчик команды для получения списка пользователей
@dp.message(Command('getusers'))
async def get_users(message: types.Message):
    # Извлекаем всех пользователей из базы данных
    cursor.execute("SELECT id, username, last_used, inline_query_count FROM users")
    users = cursor.fetchall()

    # Путь для сохранения CSV-файла
    file_path = "users.csv"

    # Создаем CSV-файл с данными пользователей
    with open(file_path, mode="w", newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # Записываем заголовки
        writer.writerow(["ID", "Username", "Last Used", "Inline Query Count"])

        # Записываем данные пользователей
        for user in users:
            writer.writerow(user)

    # Отправляем CSV-файл администратору
    await message.answer_document(FSInputFile(file_path))

    # Удаляем файл после отправки (необязательно, но рекомендуется)
    os.remove(file_path)


@dp.message(Command('listadmins'))
async def list_admins(message: types.Message):
    cursor.execute("SELECT id, username FROM admins")
    admins = cursor.fetchall()
    if admins:
        # for admin in admins:
        #     print(admin)
        admin_ids = [f'{admin[0]} - {admin[1]}' for admin in admins]
        await message.answer("Список администраторов:\n" + "\n".join(admin_ids))
    else:
        await message.answer("Список администраторов пуст.")


@dp.message(Command('addadmin'))
async def add_admin(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите ID и Имя пользователя, которого хотите назначить администратором (СТРОГО ID и чрезе пробел Имя):")
    await state.set_state(VideoState.awaiting_admin_id)  # Используйте новое состояние


@dp.message(Command('deladmin'))
async def del_admin(message: types.Message, state: FSMContext):
    await message.answer("Введите ID пользователя, которого хотите удалить из администраторов:")
    await state.set_state(VideoState.awaiting_del_admin_id)  # Используйте новое состояние


@dp.message(Command('upload'))
async def handle_upload(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте видео и описание (в следующем сообщении).")
    await state.set_state(VideoState.awaiting_video)


@dp.message(Command('updatemem'))
async def handle_updatemem(message: types.Message, state: FSMContext):
    await message.answer("Введите ID видео, которое хотите обновить:")
    await state.set_state(VideoState.awaiting_update_id)


@dp.message(Command('delmem'))
async def handle_delmem(message: types.Message, state: FSMContext):
    await message.answer("Введите ID видео, которое хотите удалить:")
    await state.set_state(VideoState.awaiting_delete_id)


# Обработчик для видео
@dp.message(F.content_type == "video")
async def handle_video(message: types.Message, state: FSMContext):
    if await state.get_state() == VideoState.awaiting_video.state:
        video: Video = message.video
        await state.update_data(file_id=video.file_id)
        await message.answer("Теперь отправьте описание для этого видео.")
        await state.set_state(VideoState.awaiting_description)


@dp.message(F.text.regexp(r"^\d+$"))
async def handle_id(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    user_input_id = int(message.text)  # Получаем ID из сообщения

    if current_state == VideoState.awaiting_update_id.state:
        cursor.execute("SELECT file_id, description FROM videos WHERE id = ?", (user_input_id,))
        result = cursor.fetchone()

        if result:
            file_id, description = result
            await state.update_data(video_id=user_input_id)
            await message.answer(f"Текущее описание: {description}\nВведите новое описание:")
            await state.set_state(VideoState.awaiting_new_description)
        else:
            await message.answer("Видео с таким ID не найдено.")
            await state.clear()

    elif current_state == VideoState.awaiting_delete_id.state:
        cursor.execute("SELECT file_id, description FROM videos WHERE id = ?", (user_input_id,))
        result = cursor.fetchone()

        if result:
            file_id, description = result
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Удалить", callback_data=f"delete:{user_input_id}"),
                    InlineKeyboardButton(text="Отменить", callback_data="cancel")
                ]
            ])

            await message.answer(
                f"Видео ID: {user_input_id}\nОписание: {description}\nЧто хотите сделать?",
                reply_markup=keyboard
            )
        else:
            await message.answer("Видео с таким ID не найдено.")
        await state.clear()

    elif current_state == VideoState.awaiting_del_admin_id.state:
        cursor.execute("DELETE FROM admins WHERE id = ?", (user_input_id,))
        conn.commit()
        await message.answer(f"Пользователь с ID {user_input_id} удален из администраторов.")
        await state.clear()


# Обработчик для описания и обновления описания
@dp.message(F.text)
async def handle_text_messages(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == VideoState.awaiting_description.state:
        description = message.text.lower()
        data = await state.get_data()
        file_id = data['file_id']

        # Сохраняем видео и описание в базе данных
        cursor.execute('INSERT INTO videos (file_id, description) VALUES (?, ?)', (file_id, description))
        conn.commit()

        await message.answer("Видео и описание сохранены!")
        await state.clear()

    elif current_state == VideoState.awaiting_new_description.state:
        new_description = message.text.lower()
        data = await state.get_data()
        video_id = data['video_id']

        # Обновляем описание в базе данных
        cursor.execute("UPDATE videos SET description = ? WHERE id = ?", (new_description, video_id))
        conn.commit()

        await message.answer("Описание обновлено!")
        await state.clear()
    elif current_state == VideoState.awaiting_admin_id.state:

        # Если мы попали в этот блок то пользователь по правилам должен был передать два слова 1-ID и 2-Название пользователя
        input_message = message.text.split(' ')
        user_input_id = int(input_message[0])  # Получаем ID из сообщения
        input_username = input_message[1]  # Получаем username из сообщения
        cursor.execute("INSERT OR IGNORE INTO admins (id, username) VALUES (?, ?)", (user_input_id, input_username))
        conn.commit()
        await message.answer(f"Пользователь с ID {user_input_id} добавлен в администраторы.")
        await state.clear()


# Обработчики колбэков для кнопок "Удалить" и "Отменить"
@dp.callback_query(F.data.startswith("delete:"))
async def delete_video_callback(callback_query: types.CallbackQuery):
    video_id = int(callback_query.data.split(":")[1])
    cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))
    conn.commit()

    await callback_query.message.edit_text(f"Видео с ID {video_id} успешно удалено.")
    await callback_query.answer()


@dp.callback_query(F.data == "cancel")
async def cancel_callback(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("Удаление отменено.")
    await callback_query.answer()


# Обработчик inline-запросов для поиска видео
@dp.inline_query()
async def inline_query_handler(inline_query: InlineQuery):
    query = inline_query.query.strip().lower()
    user_id = inline_query.from_user.id
    username = inline_query.from_user.username  # username может меняться, просто обновляем при каждом запросе
#    if username is None:
#	username = inline_query.from_user.first_name

    # Вставка или обновление информации о пользователе и увеличения счетчика запросов
    cursor.execute('''
    INSERT INTO users (id, username, last_used, inline_query_count)
    VALUES (?, ?, ?, 1)
    ON CONFLICT(id) DO UPDATE SET
        username = excluded.username,  -- обновляем username каждый раз, если он изменился
        last_used = excluded.last_used,
        inline_query_count = users.inline_query_count + 1
    ''', (user_id, username, datetime.now()))
    conn.commit()

    # Поиск видео по запросу
    if not query:
        cursor.execute("SELECT id, file_id, description, usage_count FROM videos ORDER BY usage_count DESC LIMIT 15")
    else:
        cursor.execute("SELECT id, file_id, description, usage_count FROM videos WHERE LOWER(description) LIKE ?",
                       (f'%{query}%',))

    results = cursor.fetchall()

    logging.info(f"Inline query: '{query}', found results: {len(results)}")

    videos = [
        InlineQueryResultCachedVideo(
            id=str(result[0]),
            video_file_id=result[1],
            title=f"Видео {result[0]}",
            description=result[2]
        )
        for result in results
    ]

    # Увеличиваем счетчик использования для каждого найденного видео
    if query:
        for result in results:
            cursor.execute("UPDATE videos SET usage_count = usage_count + 1 WHERE id = ?", (result[0],))
    conn.commit()

    await bot.answer_inline_query(inline_query.id, results=videos, cache_time=0)


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
