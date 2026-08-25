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
    await message.answer("Привет! Отправь мне ссылку на трек, альбом или плейлист SoundCloud, и я опубликую его в твой паблик.")

@dp.message()
async def download_soundcloud(message: types.Message):
    # 1. Находим ссылку в сообщении пользователя
    match = re.search(r'(https?://(?:on\.)?soundcloud\.com/[^\s]+)', message.text)
    if not match:
        await message.answer("Пожалуйста, отправьте корректную ссылку на SoundCloud.")
        return

    raw_url = match.group(0)
    clean_url = re.sub(r'[а-яА-Я]+$', '', raw_url)
    post_text = message.text.replace(raw_url, clean_url)

    status_message = await message.answer("Анализирую ссылку и начинаю скачивание...")

    # Базовые настройки для извлечения инфо (включаем сбор данных о плейлистах)
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'extract_flat': 'in_playlist',  # Позволяет быстро понять, плейлист это или трек
    }

    try:
        loop = asyncio.get_event_loop()
        
        # 2. Сначала отправляем очищенный текст/ссылку в твой канал
        await bot.send_message(chat_id=CHANNEL_ID, text=post_text)
        
        # 3. Извлекаем информацию о ссылке
        with YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(clean_url, download=False))
        
        # Проверяем, является ли ссылка альбомом/плейлистом
        if 'entries' in info:
            # Это альбом или плейлист!
            tracks = list(info['entries'])
            await status_message.edit_text(f"Обнаружен альбом/плейлист! Найдено треков: {len(tracks)}. Начинаю загрузку...")
            
            # Перебираем каждый трек в альбоме по очереди
            for index, track_entry in enumerate(tracks, start=1):
                track_url = track_entry.get('url') or track_entry.get('webpage_url')
                if not track_url:
                    continue
                
                await status_message.edit_text(f"Скачиваю трек {index} из {len(tracks)}...")
                await download_and_send_single_track(track_url, loop)
                
            await status_message.edit_text("✅ Все треки из альбома успешно опубликованы!")
        else:
            # Это одиночный трек!
            await status_message.edit_text("Скачиваю трек...")
            await download_and_send_single_track(clean_url, loop)
            await status_message.delete()
            
    except Exception as e:
        print(f"Ошибка при обработке: {e}")
        await status_message.edit_text("❌ Произошла ошибка при обработке ссылки.")

# Логика скачивания и отправки одного конкретного трека
async def download_and_send_single_track(url, loop):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True
    }
    
    try:
        # 1. Получаем инфо о конкретном треке
        with YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            title = info.get('title', 'Unknown Track')
            uploader = info.get('uploader', 'Unknown Artist')

        # 2. Формируем имя файла
        clean_title = re.sub(r'[\\/*?:"<>|]', "", f"{uploader} - {title}")
        
        download_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f"{clean_title}.%(ext)s",
            'quiet': True
        }

        # 3. Скачиваем
        with YoutubeDL(download_opts) as ydl:
            await loop.run_in_executor(None, lambda: ydl.download([url]))
        
        # 4. Ищем скачанный файл с любым расширением
        found_file = None
        for ext in ['mp3', 'm4a', 'ogg', 'opus', 'wav']:
            test_path = f"{clean_title}.{ext}"
            if os.path.exists(test_path):
                found_file = test_path
                break

        # 5. Если нашли — переименовываем в mp3, шлем в канал и удаляем с сервера
        if found_file:
            final_mp3 = f"{clean_title}.mp3"
            if found_file != final_mp3:
                os.rename(found_file, final_mp3)
                
            audio_file = types.FSInputFile(final_mp3)
            
            # Отправляем аудиофайл прямо в канал
            await bot.send_audio(
                chat_id=CHANNEL_ID,
                audio=audio_file, 
                title=title, 
                performer=uploader
            )
            os.remove(final_mp3)
    except Exception as e:
        print(f"Ошибка внутри download_and_send_single_track: {e}")

# Главная точка входа для удержания бота в сети
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
