import os
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from config import bot, BOT_TOKEN
from middleware import AlbumMiddleware
from aiogram.fsm.state import StatesGroup, State
from database import save_group_to_db, get_all_groups_from_db


settings_router = Router()
settings_router.message.middleware(AlbumMiddleware(latency=0.4))

class CreateMemeGroup(StatesGroup):
    waiting_for_group_name = State()
    waiting_for_group_photos = State()

@settings_router.message(Command("creategroup"))
async def create_meme_group_start(message: types.Message, state: FSMContext):
    await message.reply("Введите название новой группы мемов:")
    await state.set_state(CreateMemeGroup.waiting_for_group_name)


@settings_router.message(CreateMemeGroup.waiting_for_group_name, F.text)
async def set_group_name(message: types.Message, state: FSMContext):
    group_name = message.text
    await state.update_data(group_name=group_name)
    await save_group_to_db(group_name)
    await message.reply(f"Группа '{group_name}' создана. Отправьте фото для этой группы пачкой.")
    await state.set_state(CreateMemeGroup.waiting_for_group_photos)


@settings_router.message(CreateMemeGroup.waiting_for_group_photos, F.photo)
async def save_group_photos(message: types.Message, state: FSMContext, album: list):
    data = await state.get_data()
    group_name = data.get("group_name")

    group_folder = f"images/meme_groups/{group_name}"
    os.makedirs(group_folder, exist_ok=True)

    # Сохранение фото
    for idx, mess in enumerate(album):
        file = await bot.get_file(mess.photo[-1].file_id)
        file_path = f"{group_folder}/photo_{idx + 1}.jpg"
        await bot.download_file(file.file_path, file_path)

    await message.reply(f"Фото сохранены в группу '{group_name}'.")
    await state.clear()
