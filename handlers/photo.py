import random
import os
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from PIL import Image
from config import bot, BOT_TOKEN
from middleware import AlbumMiddleware
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, InputSticker
from aiogram.fsm.state import StatesGroup, State
from database import get_all_groups_from_db
from utils import generate_model

photos_router = Router()

photos_router.message.middleware(AlbumMiddleware(latency=0.4))

class CreateStickerPack(StatesGroup):
    waiting_for_photo_A = State()
    waiting_for_memes = State()
    waiting_for_name_pack = State()

class CreateMemeGroup(StatesGroup):
    waiting_for_group_name = State()
    waiting_for_group_photos = State()


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

    user_id = message.from_user.id
    # Сохранение фото в локальную папку
    local_dir = f"images/users/{user_id}/"
    local_file_path = f"{local_dir}{user_id}_photo_A.jpg"

    # Проверяем, существует ли директория, и создаем ее, если нужно
    if not os.path.exists(local_dir):
        os.makedirs(local_dir, exist_ok=True)

    await bot.download_file(file.file_path, local_file_path)

    # Получение списка групп из базы данных
    groups = await get_all_groups_from_db()
    print(groups)
    # Создание inline кнопок для выбора группы
    keyboard_buttons = [[]]
    for group_id, group_name in groups:
        button = InlineKeyboardButton(text=group_name, callback_data=f"select_group:{group_id}:{group_name}")
        keyboard_buttons[0].append(button)  # Добавляем кнопку
    keyboard_buttons[0].append(InlineKeyboardButton(text="Создать новую группу", callback_data="create_new_group"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons, row_width=2)

    await message.answer("Выберите группу для мемов или создайте новую:", reply_markup=keyboard)
    await state.update_data(local_file_path=local_file_path)
    await state.set_state(CreateStickerPack.waiting_for_memes)

@photos_router.callback_query(F.data.startswith("select_group:"))
async def select_group(callback_query: types.CallbackQuery, state: FSMContext):

    keyboard_buttons = [[]]
    keyboard_buttons[0].append(InlineKeyboardButton(text="Генерация", callback_data="start_gen"))
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons, row_width=2)

    # group_id = callback_query.data.split(":")[1]
    group_name = callback_query.data.split(":")[2]
    await state.update_data(selected_group=group_name)
    await callback_query.message.edit_text(f"Вы выбрали группу '{group_name}'. Нажите генерация или напишите готово, чтобы запустить процесс", reply_markup=keyboard)


@photos_router.callback_query(F.data.startswith("start_gen"))
async def generation(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("Процесс запущен. Ожидайте.")
    data = await state.get_data()
    swap_image = data.get("local_file_path")
    group_name = data.get("selected_group")

    target_images_folder = f"images/meme_groups/{group_name}"

    try:
        # Вызываем функцию
        results = await generate_model(target_images_folder, swap_image)

        # Выводим результаты
        for result in results:
            if "error" in result:
                print(f"Ошибка: {result['input']} - {result['error']}")
            else:
                print(f"Успешно обработано: {result['input']} -> {result['output']}")
        await state.update_data(paths=results)
    except Exception as e:
        print(e)
        await callback_query.message.answer("Что-пошло не так попробуйте позже.")
        await state.clear()
    finally:
        await callback_query.message.edit_text("Введите название стикерпака: ")
        await state.set_state(CreateStickerPack.waiting_for_name_pack)


@photos_router.callback_query(F.data == "create_new_group")
async def create_new_group(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("Введите название новой группы мемов:")
    await state.set_state(CreateMemeGroup.waiting_for_group_name)

@photos_router.message(CreateStickerPack.waiting_for_memes, F.photo | F.text == "готово")
async def handle_photo_meme(message: types.Message, state: FSMContext, album: list = None):
    data = await state.get_data()
    swap_image = data.get("local_file_path")
    group_name = data.get("selected_group")

    target_images_folder = f"images/meme_groups/{group_name}"

    try:
        # Вызываем функцию
        results = await generate_model(target_images_folder, swap_image)

        # Выводим результаты
        for result in results:
            if "error" in result:
                print(f"Ошибка: {result['input']} - {result['error']}")
            else:
                print(f"Успешно обработано: {result['input']} -> {result['output']}")
        await state.update_data(paths=results)
    except Exception as e:
        print(e)
        await message.answer("Что-пошло не так попробуйте позже.")
        await state.set_state(CreateStickerPack.waiting_for_name_pack)
    finally:
        await message.answer("Введите название стикерпака: ")
        await state.set_state(CreateStickerPack.waiting_for_name_pack)


# Функция для изменения размера изображения

def resize_image_to_telegram_requirements(input_path, output_path):
    """
    Изменяет размер изображения под требования Telegram для стикеров.
    """
    with Image.open(input_path) as img:
        max_size = 512  # Максимальный размер стороны
        img.thumbnail((max_size, max_size))  # Пропорциональное уменьшение
        img = img.convert("RGBA")  # Убедиться, что изображение в формате RGBA
        img.save(output_path, format="PNG")

@photos_router.message(CreateStickerPack.waiting_for_name_pack, F.text)
async def create_sticker_pack(message: types.Message, state: FSMContext):
    # Получение имени бота
    bot_username = (await bot.get_me()).username
    if not bot_username.lower().endswith("bot"):
        await message.reply("Ошибка: имя бота некорректно.")
        return

    user_id = message.from_user.id
    # Уникальное имя пакета
    sticker_pack_name = f"sticker_pack_{random.randint(1000, 9999)}_by_{bot_username}"
    sticker_pack_title = message.text.strip()  # Убираем пробелы вокруг текста
    emoji_list = ["😀", "😂", "🤣", "😍", "😎", "👍", "💪", "🔥", "😊", "🤮", "😉", "🥰"]

    # Получение путей стикеров из состояния
    data = await state.get_data()
    paths = data.get("paths", [])

    # Проверка наличия путей
    if not paths:
        await message.reply("Ошибка: пути стикеров отсутствуют.")
        return

    # Формируем список стикеров
    stickers = []
    for i, path_data in enumerate(paths):
        sticker_path = path_data.get('output')
        if not sticker_path:
            continue

        # Масштабирование изображения
        resized_path = f"./images/temp/resized_sticker_{i}.png"
        resize_image_to_telegram_requirements(sticker_path, resized_path)

        input_sticker = InputSticker(
            sticker=FSInputFile(resized_path),
            format="static",
            emoji_list=[emoji_list[i % len(emoji_list)]]
        )
        stickers.append(input_sticker)

    # Проверяем, что есть хотя бы один стикер
    if not stickers:
        await message.reply("Ошибка: не удалось создать список стикеров.")
        return

    # Создаем стикерпак
    try:
        await message.reply("Создаю стикерпак, подождите...")

        await bot.create_new_sticker_set(
            user_id=user_id,
            name=sticker_pack_name,
            title=sticker_pack_title,
            stickers=stickers,
            sticker_format="static"
        )

        await message.reply(f"Стикерпак '{sticker_pack_title}' создан успешно! Ссылка на стикерпак: https://t.me/addstickers/{sticker_pack_name}")

        # Отправляем все сгенерированные фото альбомом
        media_group = MediaGroup()
        for i, path_data in enumerate(paths):
            resized_path = f"./images/temp/resized_sticker_{i}.png"
            if os.path.exists(resized_path):
                media_group.attach_photo(FSInputFile(resized_path))

        if media_group:
            await message.answer_media_group(media_group)
    except Exception as e:
        await message.reply(f"Ошибка при создании стикерпака: {e}")

    # Удаление временных файлов
    for i, path_data in enumerate(paths):
        resized_path = f"./images/temp/resized_sticker_{i}.png"
        orig_path = path_data.get('output')
        if os.path.exists(resized_path):
            os.remove(resized_path)
        if os.path.exists(orig_path):
            os.remove(orig_path)
