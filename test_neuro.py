import aiohttp
import asyncio
import requests

def get_telegram_file_url(bot_token, file_id):
    # Получение пути к файлу
    file_info_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
    file_info_response = requests.get(file_info_url).json()
    file_path = file_info_response["result"]["file_path"]
    return f"https://api.telegram.org/file/bot/{file_path}"

async def detect_faces():
    bot_token = "1202529776:AAFRwyZ3FZ1RldD6zUjn9w7bvtamiFgn3Zw"
    file_id = "YOUR_FILE_ID"  # Замените на file_id файла в Telegram

    # Получение прямой ссылки на файл
    media_url = get_telegram_file_url(bot_token, file_id)

    url = "https://deepswapper-face-swap.p.rapidapi.com/face-swap/detect-faces"

    payload = {
        "mediaUrl": media_url
    }
    headers = {
        "x-rapidapi-key": "a168117e98mshe489e29a68a9ce2p1fdd0fjsne3d870ea8d06",
        "x-rapidapi-host": "deepswapper-face-swap.p.rapidapi.com",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            response_data = await response.json()
            print(response_data)

# Запуск асинхронной функции
asyncio.run(detect_faces())
