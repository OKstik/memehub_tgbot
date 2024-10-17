from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.methods import DeleteWebhook


from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Video, InlineQuery, InlineQueryResultCachedVideo
import logging
import sqlite3
import asyncio

API_TOKEN = '7117454247:AAHpIN4gbPdO2M8mKkbmCg1vfJqdi-SRFpk'

logging.basicConfig(level=logging.INFO)

# session = AiohttpSession(proxy='http://proxy.server:3128') # в proxy указан прокси сервер pythonanywhere, он нужен для подключения
# bot = Bot(API_TOKEN, session=session)
bot = Bot(API_TOKEN)

dp = Dispatcher(storage=MemoryStorage())

# Список id пользовтелей телеграм, которые могут работать с ботом
admin_list = [393120135, 703434028]

# Подключение к базе данных SQLite
conn = sqlite3.connect('videos.db')
cursor = conn.cursor()

# Создание таблицы, если ее нет
cursor.execute('''
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY,
    file_id TEXT NOT NULL,
    description TEXT NOT NULL
)
''')
conn.commit()


# Обработчик команды /start
@dp.message(Command('start'))
async def send_welcome(message: types.Message):
    await message.answer("Привет! Отправь /upload для загрузки видео.")


# Обработчик команды /upload
@dp.message(Command('upload'))
async def handle_upload(message: types.Message, state: FSMContext):
    if message.from_user.id in admin_list:
        await message.answer("Пожалуйста, отправьте видео и описание (в следующем сообщении).")
        await state.set_state("awaiting_video")
    else:
        await message.answer("Извините, но добовлять видео могут только админы. Для связи: @Shpakovskiy_K")


# Обработчик для сохранения видео
@dp.message(F.video)
async def handle_video(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == "awaiting_video":
        video: Video = message.video
        await state.update_data(file_id=video.file_id)
        await message.answer("Теперь отправьте описание для этого видео.")
        await state.set_state("awaiting_description")


# Обработчик для получения описания видео
@dp.message(lambda message: True)
async def handle_description(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == "awaiting_description":
        description = message.text.lower()
        data = await state.get_data()

        # Сохраняем видео и описание в базе данных
        cursor.execute('INSERT INTO videos (file_id, description) VALUES (?, ?)', (data['file_id'], description))
        conn.commit()

        await message.answer("Видео и описание сохранены!")
        await state.clear()


# Обработчик inline-запросов для поиска видео
@dp.inline_query()
async def inline_query_handler(inline_query: InlineQuery):
    query = inline_query.query.strip().lower()  # Приводим запрос к нижнему регистру и убираем лишние пробелы

    # Проверяем, если запрос пустой, возвращаем пустой результат
    if not query:
        await bot.answer_inline_query(inline_query.id, results=[], cache_time=0)
        return

    # Ищем видео, где описание содержит ключевое слово
    cursor.execute("SELECT id, file_id, description FROM videos WHERE LOWER(description) LIKE ?", (f'%{query}%',))
    results = cursor.fetchall()

    # Логируем запрос и результаты для отладки
    logging.info(f"Inline query: '{query}', found results: {len(results)}")

    # Формируем список результатов для отправки
    videos = []
    for result in results:
        video_result = InlineQueryResultCachedVideo(
            id=str(result[0]),
            video_file_id=result[1],
            title=f"Видео {result[0]}",
            description=result[2]
        )
        videos.append(video_result)

    # Если найдены подходящие видео, отправляем их, иначе отправляем пустой список
    await bot.answer_inline_query(inline_query.id, results=videos, cache_time=0)  # cache_time=0 для тестирования



async def main():
    # await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
