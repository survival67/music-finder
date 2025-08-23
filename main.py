import asyncio
import logging
import os
import tempfile

from typing import List, Dict, Any
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from yt_dlp import YoutubeDL
from aiogram.types import FSInputFile, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.storage.memory import MemoryStorage

from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

import imageio_ffmpeg as ffmpeg
ffmpeg_path = ffmpeg.get_ffmpeg_exe()

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# FSM стейт
class SearchState(StatesGroup):
    waiting_for_query = State()

# CallbackData
class SongCallbackData(CallbackData, prefix="song"):
    action: str
    index: int
    page: int

# Команды
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустити бота"),
        BotCommand(command="search", description="Пошук пісні або виконавця"),
    ]
    await bot.set_my_commands(commands)

@router.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "Привіт! Я бот для пошуку музики 🎶\n"
        "Використовуй команду /search для пошуку пісень або виконавців.\n"
    )

@router.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer(
        "Доступні команди:\n"
        "/start - Запустити бота\n"
        "/search - Пошук пісні або виконавця\n"
    )

# Поиск
@router.message(Command("search"))
async def search_handler(message: types.Message, state: FSMContext):
    await message.answer("🎵 Введіть назву пісні або ім'я виконавця:")
    await state.set_state(SearchState.waiting_for_query)

def format_duration(duration: float) -> str:
    if not duration:
        return ""
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    return f" {minutes}:{seconds:02d}"

@router.message(SearchState.waiting_for_query)
async def handle_search_request(message: types.Message, state: FSMContext):
    query = message.text.strip()
    await message.answer("🔎 Шукаю...")

    is_artist_search = (
        not any(word in query.lower() for word in ["песня", "пісня", "song", "трек", "track"]) and
        len(query.split()) < 4
    )

    ydl_opts = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "outtmpl": os.path.join(tempfile.gettempdir(), "%(title)s.%(ext)s"),
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
    "cookiefile": "cookies.txt",
    "ignoreerrors": True,
    "extractor_retries": 3,
    "retries": 3,
    "fragment_retries": 3,
    "skip_unavailable_fragments": True,
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
}

    try:
        def perform_search():
            with YoutubeDL(ydl_opts) as ydl:
                search_query = f"{query} songs" if is_artist_search else query
                info = ydl.extract_info(f"ytsearch20:{search_query}", download=False)
                return info.get('entries', [info]) if info else []

        results = await asyncio.to_thread(perform_search)

        filtered_results = [
            r for r in results if r and not any(
                x in r.get('title', '').lower() for x in
                ["live", "cover", "interview", "reaction", "album", "lyrics"]
            )
        ][:20]

        if not filtered_results:
            await message.answer("❌ Нічого не знайдено.")
            await state.clear()
            return

        await state.update_data(results=filtered_results, query=query, page=0)
        await send_page(message.chat.id, 0, filtered_results, is_artist_search)

    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        await message.answer("⚠️ Помилка під час пошуку. Спробуйте ще раз.")
        await state.clear()

async def send_page(chat_id: int, page: int, results: List[Dict[str, Any]], is_artist_search: bool = False, message: types.Message = None):
    start = page * 5
    end = start + 5
    page_items = results[start:end]

    inline_kb = []
    for i, video in enumerate(page_items, start=start):
        title = video.get('title', 'Unknown title')
        display_title = (title[:35] + '...') if len(title) > 35 else title
        duration_str = format_duration(video.get('duration'))

        inline_kb.append([
            InlineKeyboardButton(
                text=f"{display_title}{duration_str}",
                callback_data=SongCallbackData(action="download", index=i, page=page).pack()
            )
        ])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅",
                callback_data=SongCallbackData(action="prev", index=-1, page=page - 1).pack()
            )
        )
    if end < len(results):
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡",
                callback_data=SongCallbackData(action="next", index=-1, page=page + 1).pack()
            )
        )

    if nav_buttons:
        inline_kb.append(nav_buttons)

    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb)

    page_title = "Пісні виконавця" if is_artist_search else "Результати пошуку"
    text = f"{page_title} (стор. {page + 1} з {((len(results) - 1) // 5) + 1}):"

    if message:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, text, reply_markup=keyboard)

# Обработка кнопок
@router.callback_query(SongCallbackData.filter())
async def process_callback(callback: CallbackQuery, callback_data: SongCallbackData, state: FSMContext):
    data = await state.get_data()
    results = data.get("results", [])
    query = data.get("query", "")
    is_artist_search = (
        not any(word in query.lower() for word in ["песня", "пісня", "song", "трек", "track"]) and
        len(query.split()) < 4
    )

    if callback_data.action in ["next", "prev"]:
        await state.update_data(page=callback_data.page)
        await send_page(
            chat_id=callback.message.chat.id,
            page=callback_data.page,
            results=results,
            is_artist_search=is_artist_search,
            message=callback.message
        )
        await callback.answer()
        return

    if callback_data.action == "download":
        if 0 <= callback_data.index < len(results):
            video = results[callback_data.index]
            await callback.message.answer(f"⏳ Завантажую: {video.get('title', 'audio')}")

            video_id = video.get('id')
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            ydl_opts = {
                "format": "bestaudio/best",
                "noplaylist": True,
                "quiet": True,
                "outtmpl": os.path.join(tempfile.gettempdir(), "%(title)s.%(ext)s"),
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                 }],
                "cookiefile": "cookies.txt",
                "ignoreerrors": True,
                "extractor_retries": 3,
                "retries": 3,
                "fragment_retries": 3,
                "skip_unavailable_fragments": True,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
            }

            try:
                def download_audio():
                    with YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(video_url, download=True)
                        filename = ydl.prepare_filename(info)
                        # Жестко меняем расширение на .mp3
                        filename = os.path.splitext(filename)[0] + ".mp3"
                        return filename, info.get('title', 'audio')

                filename, title = await asyncio.to_thread(download_audio)

                if not os.path.exists(filename) or os.path.getsize(filename) == 0:
                    await callback.message.answer("⚠️ Помилка: файл не знайдено або він пустий.")
                    return

                audio_file = FSInputFile(path=filename, filename=os.path.basename(filename))

                try:
                    await callback.message.answer_document(audio_file, caption=title[:64])
                finally:
                    # Видаляємо файл після відправки
                    if os.path.exists(filename):
                        os.remove(filename)

            except Exception as e:
                logger.error(f"Download error: {e}", exc_info=True)
                await callback.message.answer("⚠️ Помилка при завантаженні аудіо. Спробуйте ще раз.")
        else:
            await callback.message.answer("❌ Невірний вибір.")

    await callback.answer()

# Запуск
dp.include_router(router)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await set_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот призупинено.")
