import asyncio
from asyncio import Queue
import os
import time
from config import bot, model_semaphore, model_pool
from states import CreateStickerPack

# Глобальная очередь задач
task_queue = Queue()

# Обработчик задач
async def task_worker():
    while True:
        user_id, task_data = await task_queue.get()
        async with model_semaphore:  # Ждем свободной модели
            predictor = model_pool.pop(0)  # Берем модель из пула
            try:
                # Выполняем задачу
                result, total_images, total_duration, photos_per_second = await asyncio.to_thread(
                    generate_model,
                    predictor,
                    task_data["target_folder"],
                    task_data["swap_image"],
                    user_id
                )
                # Сохраняем результаты
                await task_data["state"].update_data(paths=result)
                await task_data["state"].set_state(CreateStickerPack.waiting_for_name_pack)
                print(total_images, total_duration, photos_per_second)
                await bot.send_message(user_id, f"Ваша задача выполнена!\nВведите название стикерпака: ")
            except Exception as e:
                print(f"Ошибка выполнения задачи для пользователя {user_id}: {e}")
                await bot.send_message(user_id, "Возникла ошибка при обработке вашей задачи.")
            finally:
                # Возвращаем модель в пул
                model_pool.append(predictor)
                task_queue.task_done()

def send_request_to_model(predictor, target_image, swap_image, user_id):
    result = predictor.predict(target_image, swap_image, user_id)
    if result:
        return result
    return None


def generate_model(predictor, target_images_path, swap_image_path, user_id):
    """
    Обрабатывает папку с целевыми изображениями и одно свап-изображение,
    выполняет асинхронные запросы для создания новых изображений.

    :param target_images_path: Путь к папке с целевыми изображениями.
    :param swap_image_path: Путь к изображению для замены.
    :return: Список с результатами обработки.
    """
    # Проверяем, существует ли путь
    if not os.path.exists(target_images_path):
        raise FileNotFoundError(f"Папка с целевыми изображениями не найдена: {target_images_path}")

    if not os.path.exists(swap_image_path):
        raise FileNotFoundError(f"Свап-изображение не найдено: {swap_image_path}")

    print(target_images_path, swap_image_path)

    # Собираем пути ко всем файлам в папке с целевыми изображениями
    target_images = [
        os.path.join(target_images_path, file_name)
        for file_name in os.listdir(target_images_path)
        if os.path.isfile(os.path.join(target_images_path, file_name))
    ]

    total_images = len(target_images)  # Общее количество изображений
    start_time = time.time()

    # Асинхронно обрабатываем каждое целевое изображение
    def process_target_image(target_image_path):

        # Отправляем запрос на API
        print(target_image_path, " send to models")
        result_output = send_request_to_model(predictor, target_image_path, swap_image_path, user_id)

        print(result_output)

        if result_output:
            return {"input": target_image_path, "output": result_output}
        else:
            return {"input": target_image_path, "error": "Failed to process image"}

    # Запускаем обработку изображений параллельно
    results = [process_target_image(path) for path in target_images]

    end_time = time.time()
    total_duration = end_time - start_time  # Общее время выполнения

    # Рассчитываем количество фото на время
    photos_per_second = total_images / total_duration if total_duration > 0 else 0

    return results, total_images, total_duration, photos_per_second
