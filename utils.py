import asyncio
import aiohttp
import base64
import os
from config import predictor

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
            try:
                response_data = await response.json()
                print(response_data)
                return response_data
            except aiohttp.ContentTypeError:
                print("Error decoding JSON response from detect_faces.")
                return {}


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
            try:
                response_data = await response.json()
                print(response_data)
                return response_data
            except aiohttp.ContentTypeError:
                print("Error decoding JSON response from start_swap.")
                return {}

async def get_swap_status(job_id):
    url = f"https://deepswapper-face-swap.p.rapidapi.com/face-swap/status/{job_id}"

    headers = {
        "x-rapidapi-key": "a168117e98mshe489e29a68a9ce2p1fdd0fjsne3d870ea8d06",
        "x-rapidapi-host": "deepswapper-face-swap.p.rapidapi.com"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            try:
                response_data = await response.json()
                print(response_data)
                return response_data
            except aiohttp.ContentTypeError:
                print("Error decoding JSON response from get_swap_status.")
                return {}


async def check_swap_status(jobs):
    """
    Функция проверяет статус задач до тех пор, пока все не будут иметь статус 'completed'.
    """
    completed_jobs = set()  # Множество завершённых job_id
    results = {}  # Словарь с результатами завершённых задач

    while len(completed_jobs) < len(jobs):
        # Проверяем статус только для незавершённых задач
        pending_jobs = [job for job in jobs if job['jobId'] not in completed_jobs]
        statuses = await asyncio.gather(*[get_swap_status(job['jobId']) for job in pending_jobs])

        for job, status in zip(pending_jobs, statuses):
            if status.get("status") == "completed":
                completed_jobs.add(job['jobId'])  # Добавляем job_id в завершённые
                results[job['jobId']] = status.get("result").get("mediaUrl")  # Сохраняем URL результата

        await asyncio.sleep(10)  # Ждём перед следующей проверкой

    return results

async def send_request(target_image_base64, swap_image_base64):
    url = "https://memezaway-swap-face-model.hf.space/api/predict"

    # Подготовка payload с base64 данными изображений
    payload = {
        "data": [
            f'data:image/png;base64,{target_image_base64}',  # Здесь будет base64 строка для изображения "Target Image"
            f'data:image/png;base64,{swap_image_base64}'     # Здесь будет base64 строка для изображения "Swap Image"
        ]
    }

    # Заголовки запроса
    headers = {
        'Content-Type': 'application/json'
    }

    # Отправка асинхронного POST запроса
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as response:
            if response.status == 200:
                # Получение ответа в виде JSON
                response_data = await response.json()
                result_image_base64 = response_data['data'][0]  # Получаем base64 данных результата
                duration = response_data['duration']  # Получаем время выполнения
                return result_image_base64, duration
            else:
                print(f"Error: {response.status} {response}")
                return None, None

async def send_request_to_model(target_image, swap_image):
    output_path = predictor.predict(target_image, swap_image)
    if output_path:
        return output_path
    return ""

def save_base64_image(base64_str, output_filename):
    # Убираем префикс 'data:image/png;base64,' если он есть
    if base64_str.startswith('data:image'):
        base64_str = base64_str.split(',')[1]

    # Декодируем строку base64 в байты
    image_data = base64.b64decode(base64_str)

    # Сохраняем байты в файл
    with open(output_filename, 'wb') as output_file:
        output_file.write(image_data)
        print(f"Изображение сохранено в файл: {output_filename}")

async def generate_base64(target_images_path, swap_image_path):
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

    # Кодируем свап-изображение в Base64
    with open(swap_image_path, "rb") as swap_file:
        swap_image_base64 = base64.b64encode(swap_file.read()).decode('utf-8')

    # Собираем пути ко всем файлам в папке с целевыми изображениями
    target_images = [
        os.path.join(target_images_path, file_name)
        for file_name in os.listdir(target_images_path)
        if os.path.isfile(os.path.join(target_images_path, file_name))
    ]

    # Асинхронно обрабатываем каждое целевое изображение
    async def process_target_image(target_image_path):
        # Кодируем изображение в Base64
        with open(target_image_path, "rb") as target_file:
            target_image_base64 = base64.b64encode(target_file.read()).decode('utf-8')

        # Отправляем запрос на API
        print(target_image_base64[:50], " send")
        result_base64, duration = await send_request_to_model(target_image_base64, swap_image_base64)
        if result_base64:
            # Сохраняем результат в файл
            output_filename = os.path.join(
                target_images_path, f"output/output_{os.path.basename(target_image_path)}"
            )
            save_base64_image(result_base64, output_filename)
            return {"input": target_image_path, "output": output_filename, "duration": duration}
        else:
            return {"input": target_image_path, "error": "Failed to process image"}

    # Запускаем обработку изображений параллельно
    results = await asyncio.gather(*[process_target_image(path) for path in target_images])

    return results


async def generate_model(target_images_path, swap_image_path):
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

    # Асинхронно обрабатываем каждое целевое изображение
    async def process_target_image(target_image_path):

        # Отправляем запрос на API
        print(target_image_path, " send to model")
        result_output = await send_request_to_model(target_image_path, swap_image_path)

        if result_output:
            return {"input": target_image_path, "output": result_output}
        else:
            return {"input": target_image_path, "error": "Failed to process image"}

    # Запускаем обработку изображений параллельно
    results = await asyncio.gather(*[process_target_image(path) for path in target_images])

    return results
