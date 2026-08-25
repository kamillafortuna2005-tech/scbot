import asyncio
import os
import re
import shutil
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from yt_dlp import YoutubeDL

TOKEN = "8867316822:AAFaa_bFHywtu1UqRwCTGHoK78ljlr-Kfrg"
CHANNEL_ID = "@musicCEO228"  # Юзернейм твоего паблика
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("Привет! Отправь мне ссылку на трек или альбом SoundCloud, и я опубликую его в твой паблик одной группой.")

@dp.message()
async def download_soundcloud(message: types.Message):
    # 1. Находим и очищаем ссылку
    match = re.search(r'(https?://(?:on\.)?soundcloud\.com/[^\s]+)', message.text)
    if not match:
        await message.answer("Пожалуйста, отправьте корректную ссылку на SoundCloud.")
        return

    raw_url = match.group(0)
    clean_url = re.sub(r'[а-яА-Я]+$', '', raw_url)
    post_text = message.text.replace(raw_url, clean_url)

    status_message = await message.answer("Анализирую релиз и начинаю скачивание...")

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'extract_flat': 'in_playlist',
    }

    # Создаем уникальную временную папку для сбора треков этого деплоя/запроса
    session_dir = f"download_{message.message_id}"
    os.makedirs(session_dir, exist_ok=True)

    try:
        loop = asyncio.get_event_loop()
        
        with YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(clean_url, download=False))
        
        media_batch = []  # Список для собранных треков

        # 2. Собираем треки (плейлист или сингл)
        if 'entries' in info:
            tracks = list(info['entries'])
            await status_message.edit_text(f"Обнаружен альбом! Найдено треков: {len(tracks)}. Скачиваю на сервер...")
            
            for index, track_entry in enumerate(tracks, start=1):
                track_url = track_entry.get('url') or track_entry.get('webpage_url')
                if not track_url:
                    continue
                await status_message.edit_text(f"Загрузка на сервер: трек {index} из {len(tracks)}...")
                file_info = await download_single_file(track_url, loop, session_dir)
                if file_info:
                    media_batch.append(file_info)
        else:
            await status_message.edit_text("Скачиваю сингл на сервер...")
            file_info = await download_single_file(clean_url, loop, session_dir)
            if file_info:
                media_batch.append(file_info)

        # 3. Публикация, если файлы успешно скачались
        if media_batch:
            await status_message.edit_text("Все файлы на сервере. Начинаю публикацию...")
            
            # Сначала отправляем текстовую ссылку
            await bot.send_message(chat_id=CHANNEL_ID, text=post_text)
            
            # Нарезаем массив треков на группы максимум по 10 штук (лимит Telegram)
            for i in range(0, len(media_batch), 10):
                chunk = media_batch[i:i+10]
                media_group = []
                
                for item in chunk:
                    audio_file = types.FSInputFile(item['path'])
                    media_group.append(
                        types.InputMediaAudio(
                            media=audio_file,
                            title=item['title'],
                            performer=item['performer']
                        )
                    )
                
                # Отправляем пачку треков ОДНИМ сообщением
                await bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
                await asyncio.sleep(1)  # Защита от флуд-фильтра Telegram
            
            await status_message.edit_text("✅ Альбом успешно опубликован в одном сообщении!")
        else:
            await status_message.edit_text("❌ Не удалось скачать ни одного трека.")

    except Exception as e:
        print(f"Ошибка при обработке релиза: {e}")
        await status_message.edit_text("❌ Произошла ошибка при обработке ссылки.")
    
    finally:
        # Полностью вычищаем за собой временную папку с аудиофайлами
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)

# Вспомогательная функция для скачивания файла во временную папку
async def download_single_file(url, loop, save_dir):
    ydl_opts = {'format': 'bestaudio/best', 'quiet': True}
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            title = info.get('title', 'Unknown Track')
            uploader = info.get('uploader', 'Unknown Artist')

        clean_title = re.sub(r'[\\/*?:"<>|]', "", f"{uploader} - {title}")
        
        # Сохраняем строго во временную сессионную папку
        download_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(save_dir, f"{clean_title}.%(ext)s"),
            'quiet': True
        }

        with YoutubeDL(download_opts) as ydl:
            await loop.run_in_executor(None, lambda: ydl.download([url]))
        
        # Находим расширение
        for ext in ['mp3', 'm4a', 'ogg', 'opus', 'wav']:
            test_path = os.path.join(save_dir, f"{clean_title}.{ext}")
            if os.path.exists(test_path):
                final_mp3 = os.path.join(save_dir, f"{clean_title}.mp3")
                if test_path != final_mp3:
                    os.rename(test_path, final_mp3)
                return {'path': final_mp3, 'title': title, 'performer': uploader}
    except Exception as e:
        print(f"Ошибка при скачивании трека {url}: {e}")
    return None

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
