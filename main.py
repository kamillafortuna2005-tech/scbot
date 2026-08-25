import asyncio
import os
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from yt_dlp import YoutubeDL

TOKEN = "8867316822:AAFaa_bFHywtu1UqRwCTGHoK78ljlr-Kfrg"
CHANNEL_ID = "@percshawty"  # Юзернейм твоего паблика
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("Привет! Отправь мне ссылку на трек SoundCloud, и я опубликую его в твой паблик.")

@dp.message()
async def download_soundcloud(message: types.Message):
    # 1. Находим ссылку в сообщении пользователя
    match = re.search(r'(https?://(?:on\.)?soundcloud\.com/[^\s]+)', message.text)
    if not match:
        await message.answer("Пожалуйста, отправьте корректную ссылку на SoundCloud.")
        return

    # Запоминаем грязную ссылку, вырезанную из текста
    raw_url = match.group(0)
    
    # Очищаем её от случайных русских букв на конце
    clean_url = re.sub(r'[а-яА-Я]+$', '', raw_url)
    
    # 2. Формируем текст поста: берем исходный текст пользователя и заменяем в нем грязную ссылку на чистую
    post_text = message.text.replace(raw_url, clean_url)

    status_message = await message.answer("Начинаю скачивание, подождите...")

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True
    }

    try:
        loop = asyncio.get_event_loop()
        
        # 3. Извлекаем информацию о треке без скачивания
        with YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(clean_url, download=False))
            title = info.get('title', 'Unknown Track')
            uploader = info.get('uploader', 'Unknown Artist')

        # 4. Формируем имя файла без опасных символов
        clean_title = re.sub(r'[\\/*?:"<>|]', "", f"{uploader} - {title}")
        
        download_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f"{clean_title}.%(ext)s",
            'quiet': True
        }

        # 5. Скачиваем трек с правильным именем
        with YoutubeDL(download_opts) as ydl:
            await loop.run_in_executor(None, lambda: ydl.download([clean_url]))
        
        # 6. Ищем, какой файл создался на диске
        found_file = None
        for ext in ['mp3', 'm4a', 'ogg', 'opus', 'wav']:
            test_path = f"{clean_title}.{ext}"
            if os.path.exists(test_path):
                found_file = test_path
                break

        # 7. Переименовываем в .mp3, отправляем в паблик и удаляем
        if found_file:
            final_mp3 = f"{clean_title}.mp3"
            if found_file != final_mp3:
                os.rename(found_file, final_mp3)
                
            await status_message.edit_text("Файл скачан! Публикую в паблик...")
            audio_file = types.FSInputFile(final_mp3)
            
            # Отправляем очищенный текст в твой канал
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=post_text
            )
            
            # Отправляем сам аудиофайл в твой канал следующим сообщением
            await bot.send_audio(
                chat_id=CHANNEL_ID,
                audio=audio_file, 
                title=title, 
                performer=uploader
            )
            
            os.remove(final_mp3)
            await status_message.edit_text("✅ Успешно опубликовано в паблике!")
        else:
            await status_message.edit_text("❌ Ошибка: не удалось найти скачанный аудиофайл.")
            
    except Exception as e:
        print(f"Ошибка при скачивании: {e}")
        await status_message.edit_text("❌ Произошла ошибка при обработке ссылки.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
