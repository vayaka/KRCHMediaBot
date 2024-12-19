from aiogram.fsm.state import StatesGroup, State

class CreateStickerPack(StatesGroup):
    waiting_for_photo_A = State()
    waiting_for_memes = State()
    waiting_for_name_pack = State()

class CreateMemeGroup(StatesGroup):
    waiting_for_group_name = State()
    waiting_for_group_photos = State()
