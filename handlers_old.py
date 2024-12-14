import asyncio
import aiohttp
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from config import bot, BOT_TOKEN
from middleware import AlbumMiddleware
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ContentType, InputFile
from utils import check_swap_status, detect_faces, start_swap, get_swap_status

photos_router = Router()

photos_router.message.middleware(AlbumMiddleware(latency=0.4))

class CreateStickerPack(StatesGroup):
    waiting_for_photo_A = State()
    waiting_for_memes = State()
    waiting_for_name_pack = State()


@photos_router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    welcome_text = (
        "Привет! Я бот для создания стикерпаков от Короче Медиа. \n"
        "Вот что я умею:\n"
        "- Отправьте мне фото известного человека, и я сделаю его лицо в мемах.\n"
        "Попробуйте отправить фото прямо сейчас!"
    )
    await message.reply(welcome_text)
    await state.set_state(CreateStickerPack.waiting_for_photo_A)

@photos_router.message(CreateStickerPack.waiting_for_photo_A, F.photo)
async def handle_photo_A(message: types.Message, state: FSMContext):
    # Получение информации о файле
    file = await bot.get_file(message.photo[-1].file_id)

    # Генерация прямой ссылки на файл
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    await state.update_data(new_face_url=file_url)
    await message.answer("Отправьте фото мемов пачкой 10-12 штук")
    await state.set_state(CreateStickerPack.waiting_for_memes)


@photos_router.message(CreateStickerPack.waiting_for_memes, F.photo)
async def handle_photo_meme(message: types.Message, state: FSMContext, album: list):
    data = await state.get_data()
    new_face_url = data.get("new_face_url")

    await message.reply(f"Было полученно {len(album)} фото. Обработка начата. Ожидайте примерно 30сек.")

    # Получение информации о файле
    files = await asyncio.gather(*[bot.get_file(mess.photo[-1].file_id) for mess in album])

    # Генерируем ссылки
    files_url = [f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}" for file in files]

    # Вызов detect_faces для каждого файла
    detect_results = await asyncio.gather(*[detect_faces(url) for url in files_url])

    # Получение первых элементов (предполагается, что detect_faces возвращает списки)
    faces = [result[-1] for result in detect_results if result]  # Убедитесь, что result не None

    jobs = await asyncio.gather(*[start_swap(url, face, new_face_url) for url, face in zip(files_url, faces)])

    await asyncio.sleep(30)
    # Получение информации о результатах
    # jobs - список идентификаторов задач, которые нужно проверить
    results = await check_swap_status(jobs)

    # results содержит {job_id: result_url} для завершённых задач
    for job, result_url in results.items():
        print(f"Задача {job} завершена. Результат: {result_url}")

    await message.answer(f"{faces}\n"
                         f"{jobs}\n"
                         f"{results}")

    await state.update_data(urls=results)
    await message.answer("Введите название стикерпака: ")
    await state.set_state(CreateStickerPack.waiting_for_name_pack)

@photos_router.message(CreateStickerPack.waiting_for_name_pack, F.text)
async def create_sticker_pack(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    sticker_pack_name = f"custom_pack_by_{BOT_TOKEN[:8]}"  # Уникальное имя пакета
    sticker_pack_title = message.text
    emoji = "😀"

    # Список URL для загрузки
    data = await state.get_data()
    results = data.get("urls")

    try:
        # Создание первого стикера
        first_sticker_url = next(iter(results.values()))  # Получаем URL первого стикера
        async with aiohttp.ClientSession() as session:
            async with session.get(first_sticker_url) as resp:
                if resp.status == 200:
                    with open("sticker_image_0.png", "wb") as f:
                        f.write(await resp.read())

        await bot.create_new_sticker_set(
            user_id=user_id,
            name=sticker_pack_name,
            title=sticker_pack_title,
            png_sticker=InputFile("sticker_image_0.png"),
            emojis=emoji
        )
        await message.reply(f"Стикерпак '{sticker_pack_title}' создан! Добавляю остальные стикеры...")

        # Добавление остальных стикеров
        for i, (job_id, url) in enumerate(results.items()):
            if i == 0:
                continue  # Первый стикер уже добавлен

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
