import asyncio
import logging
from config import dp, bot
from handlers import photo, settings
import database
from utils import task_worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    dp.include_routers(photo.photos_router, settings.settings_router)
    asyncio.create_task(task_worker())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
