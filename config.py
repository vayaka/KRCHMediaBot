import os
from asyncio import Semaphore
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from app import Predictor

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Устанавливаем размер пула (например, 3 одновременные задачи)
MODEL_POOL_SIZE = 6
model_semaphore = Semaphore(MODEL_POOL_SIZE)

# Инициализируем пул моделей
model_pool = [Predictor() for _ in range(MODEL_POOL_SIZE)]
