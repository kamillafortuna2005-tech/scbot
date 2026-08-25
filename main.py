import asyncio
import os
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from yt_dlp import YoutubeDL

TOKEN = "8867316822:AAFaa_bFHywtu1UqRwCTGHoK78ljlr-Kfrg"
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("Привет! Отправь мне ссылку на трек SoundCloud, и я его скачаю.")

@dp.message()
async def download_soundcloud(message: types.Message):
    match = re.search(r'(https?://(?:on\.)?soundcloud\.com/[^\s]+)', message.text)
    if not match:
        await message.answer("Пожалуйста, отправьте корректную ссылку на SoundCloud.")
        return

    url = match.group(0)
    url = re.sub(r'[а-яА-Я]+$', '', url)
    status_message = await message.answer("Начинаю скачивание, подождите...")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'track.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True
    }

    try:
        loop = asyncio.get_event_loop()
        with YoutubeDL(ydl_opts) as ydl:
            await loop.run_in_executor(None, lambda: ydl.download([url]))
        
        file_path = "track.mp3"
        if os.path.exists(file_path):
            await status_message.edit_text("Файл успешно скачан! Отправляю в Telegram...")
            audio_file = types.FSInputFile(file_path)
            await message.answer_audio(audio=audio_file)
            os.remove(file_path)
            await status_message.delete()
        else:
            await status_message.edit_text("❌ Ошибка: не удалось сохранить аудиофайл.")
    except Exception as e:
        print(f"Ошибка при скачивании: {e}")
        await status_message.edit_text("❌ Произошла ошибка при обработке ссылки. Возможно, трек скрыт или заблокирован.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
