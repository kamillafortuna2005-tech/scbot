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
    # 1. Вытаскиваем ссылку из любого грязного текста и убираем русские буквы на конце
    match = re.search(r'(https?://(?:on\.)?soundcloud\.com/[^\s]+)', message.text)
    if not match:
        await message.answer("Пожалуйста, отправьте корректную ссылку на SoundCloud.")
        return

    url = match.group(0)
    url = re.sub(r'[а-яА-Я]+$', '', url)
    status_message = await message.answer("Начинаю скачивание, подождите...")

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True
    }

    try:
        loop = asyncio.get_event_loop()
        with YoutubeDL(ydl_opts) as ydl:
            # 2. Сначала получаем инфу о треке, чтобы узнать имя автора и название
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            title = info.get('title', 'Unknown Track')
            uploader = info.get('uploader', 'Unknown Artist')

            # 3. Чистим имя от запрещенных символов Windows/Linux для названий файлов
            clean_title = re.sub(r'[\\/*?:"<>|]', "", f"{uploader} - {title}")
            
            # Исправлено: правильный ключ параметров outtmpl вместо outtmlp
            ydl.params['outtmpl'] = f"{clean_title}.%(ext)s"

            # 4. Скачиваем сам трек
            await loop.run_in_executor(None, lambda: ydl.download([url]))

        # 5. Ищем, с каким расширением yt-dlp реально сохранил аудио (обычно .m4a или .opus)
        found_file = None
        for ext in ['mp3', 'm4a', 'ogg', 'opus', 'wav']:
            test_path = f"{clean_title}.{ext}"    
            if os.path.exists(test_path):
                found_file = test_path
                break

        if found_file:
            final_mp3 = f"{clean_title}.mp3"
            
            # Исправлено: добавлено нижнее подчеркивание в final_mp3
            if found_file != final_mp3:
                os.rename(found_file, final_mp3)

            await status_message.edit_text("Файл успешно скачан! Отправляю в Telegram...")
            audio_file = types.FSInputFile(final_mp3)
            
            # 6. Отправляем красивый аудиофайл с тегами автора и названия в плеер Telegram
            await message.answer_audio(
                audio=audio_file,
                title=title,
                performer=uploader
            )
            
            # Исправлено: удаляем именно final_mp3 вместо несуществующей file_path
            os.remove(final_mp3)
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
