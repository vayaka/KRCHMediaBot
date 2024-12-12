import os
import aiohttp
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Инициализация бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class CreateStickerPack(StatesGroup):
    waiting_for_photo_A = State()
    waiting_for_memes = State()
    waiting_for_name_pack = State()

async def detect_faces(media_url):
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
    return response_data


async def start_swap(media_url, faces, new_face_url):
    url = "https://deepswapper-face-swap.p.rapidapi.com/face-swap/start-swap"

    payload = {
        "mediaUrl": media_url,
        "faces": [
            {
                "newFace": new_face_url,
                "originalFace": faces
            }
        ]
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
    return response_data.get("jobId", None)

async def get_swap_status(job_id):
    url = f"https://deepswapper-face-swap.p.rapidapi.com/face-swap/status/{job_id}"

    headers = {
        "x-rapidapi-key": "a168117e98mshe489e29a68a9ce2p1fdd0fjsne3d870ea8d06",
        "x-rapidapi-host": "deepswapper-face-swap.p.rapidapi.com"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            response_data = await response.json()
            print(response_data)
    return response_data.get('result', None).get("mediaUrl", "")

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    welcome_text = (
        "Привет! Я бот для создания стикерпаков от Короче Медиа. \n"
        "Вот что я умею:\n"
        "- Отправьте мне фото известного человека, и я сделаю его лицо в мемах.\n"
        "Попробуйте отправить фото прямо сейчас!"
    )
    await message.reply(welcome_text)
    await state.set_state(CreateStickerPack.waiting_for_photo_A)

@dp.message(CreateStickerPack.waiting_for_photo_A, F.photo)
async def handle_photo_A(message: types.Message, state: FSMContext):
    # Получение информации о файле
    file = await bot.get_file(message.photo[0].file_id)

    # Генерация прямой ссылки на файл
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    await state.update_data(new_face_url=file_url)
    await message.answer("Отправьте фото мемов пачкой 10-12 штук")
    await state.set_state(CreateStickerPack.waiting_for_memes)


@dp.message(CreateStickerPack.waiting_for_memes, F.photo)
async def handle_photo_meme(message: types.Message, state: FSMContext):
    data = await state.get_data()
    new_face_url = data.get("new_face_url")
    # Получение информации о файле
    files = await asyncio.gather(*[bot.get_file(x.file_id) for x in message.photo])

    # Генерируем ссылки
    files_url = [f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}" for file in files]

    await message.answer(f"{files_url}")

    # Вызов detect_faces для каждого файла
    detect_results = await asyncio.gather(*[detect_faces(url) for url in files_url])

    # Получение первых элементов (предполагается, что detect_faces возвращает списки)
    faces = [result[0] for result in detect_results if result]  # Убедитесь, что result не None

    jobs = await asyncio.gather(*[start_swap(url, face, new_face_url) for url, face in zip(files_url, faces)])

    urls_done = await asyncio.gather(*[get_swap_status(job) for job in jobs])

    await message.answer(f"{faces}\n"
                         f"{jobs}\n"
                         f"{urls_done}")

    await state.update_data(urls=urls_done)
    await message.answer("Введите название стикерпака: ")
    await state.set_state(CreateStickerPack.waiting_for_name_pack)

@dp.message(CreateStickerPack.waiting_for_name_pack, F.text)
async def create_sticker_pack(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    sticker_pack_name = f"custom_pack_by_{BOT_TOKEN[:8]}"  # Уникальное имя пакета
    sticker_pack_title = message.text
    emoji = "😀"

    # Список URL для загрузки
    data = await state.get_data()
    photo_urls = data.get('urls')

    # Создание первого стикера (обязательно для создания пакета)
    async with aiohttp.ClientSession() as session:
        async with session.get(photo_urls[0]) as resp:
            if resp.status == 200:
                with open("sticker_image_0.png", "wb") as f:
                    f.write(await resp.read())

    try:
        await bot.create_new_sticker_set(
            user_id=user_id,
            name=sticker_pack_name,
            title=sticker_pack_title,
            png_sticker=InputFile("sticker_image_0.png"),
            emojis=emoji
        )
        await message.reply(f"Стикерпак '{sticker_pack_title}' создан! Добавляю остальные стикеры...")

        # Добавление остальных стикеров
        for i, url in enumerate(photo_urls[1:], start=1):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        with open(f"sticker_image_{i}.png", "wb") as f:
                            f.write(await resp.read())

            await bot.add_sticker_to_set(
                user_id=user_id,
                name=sticker_pack_name,
                png_sticker=InputFile(f"sticker_image_{i}.png"),
                emojis=emoji
            )

        await message.reply(f"Все стикеры добавлены в '{sticker_pack_title}'!")
    except Exception as e:
        await message.reply(f"Ошибка при создании стикерпака: {e}")



async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
