import insightface
import os
import onnxruntime
import cv2
import gfpgan
import tempfile
import time
# import asyncio
# import os
# import aiofiles
# from aiohttp import ClientSession
# import cv2
# from insightface.app import FaceAnalysis
# from insightface.model_zoo import get_model
# from gfpgan import GFPGANer
# from concurrent.futures import ThreadPoolExecutor

# class AsyncPredictor:
#     def __init__(self):
#         self.face_swapper = None
#         self.face_enhancer = None
#         self.face_analyser = None
#         self.executor = ThreadPoolExecutor()

#     async def setup(self):
#         os.makedirs('models', exist_ok=True)

#         # Асинхронная загрузка моделей
#         if not os.path.exists('models/GFPGANv1.4.pth'):
#             async with ClientSession() as session:
#                 async with session.get(
#                         'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth') as resp:
#                     async with aiofiles.open('models/GFPGANv1.4.pth', 'wb') as f:
#                         await f.write(await resp.read())

#         if not os.path.exists('models/inswapper_128.onnx'):
#             async with ClientSession() as session:
#                 async with session.get(
#                         'https://huggingface.co/ashleykleynhans/inswapper/resolve/main/inswapper_128.onnx') as resp:
#                     async with aiofiles.open('models/inswapper_128.onnx', 'wb') as f:
#                         await f.write(await resp.read())

#         # Инициализация моделей
#         self.face_swapper = get_model('models/inswapper_128.onnx')
#         self.face_enhancer = GFPGANer(model_path='models/GFPGANv1.4.pth', upscale=1)
#         self.face_analyser = FaceAnalysis(name='buffalo_l')
#         self.face_analyser.prepare(ctx_id=0, det_size=(640, 640))

#     def process_image_sync(self, input_image_path, swap_image_path):
#         """
#         Обработка изображений в синхронном режиме (для запуска в отдельном потоке).
#         """
#         frame = cv2.imread(input_image_path)
#         face = self.face_analyser.get(frame)[0]
#         source_face = self.face_analyser.get(cv2.imread(swap_image_path))[0]

#         result = self.face_swapper.get(frame, face, source_face, paste_back=True)
#         _, _, result = self.face_enhancer.enhance(result, paste_back=True)
#         return result

#     async def predict(self, input_image_path, swap_image_path):
#         """
#         Асинхронная генерация картинок.
#         """
#         try:
#             # Выполнение обработки в отдельном потоке
#             result = await asyncio.to_thread(self.process_image_sync, input_image_path, swap_image_path)

#             # Сохранение результата асинхронно
#             output_path = f"./images/temp/{int(time.time())}.jpg"
#             os.makedirs(os.path.dirname(output_path), exist_ok=True)
#             async with aiofiles.open(output_path, 'wb') as f:
#                 _, buffer = cv2.imencode('.jpg', result)
#                 await f.write(buffer.tobytes())

#             return output_path
#         except Exception as e:
#             print(f"Ошибка при предсказании: {e}")
#             return None


class Predictor:
    def __init__(self):
        self.setup()

    def setup(self):
        os.makedirs('models', exist_ok=True)
        os.chdir('models')
        if not os.path.exists('GFPGANv1.4.pth'):
            os.system(
                'wget https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth'
            )
        if not os.path.exists('inswapper_128.onnx'):
            os.system(
                'wget https://huggingface.co/ashleykleynhans/inswapper/resolve/main/inswapper_128.onnx'
            )
        os.chdir('..')

        """Load the model into memory to make running multiple predictions efficient"""
        self.face_swapper = insightface.model_zoo.get_model('models/inswapper_128.onnx',
                                                            providers=onnxruntime.get_available_providers())
        self.face_enhancer = gfpgan.GFPGANer(model_path='models/GFPGANv1.4.pth', upscale=1)
        self.face_analyser = insightface.app.FaceAnalysis(name='buffalo_l')
        self.face_analyser.prepare(ctx_id=0, det_size=(640, 640))

    def get_face(self, img_data):
        analysed = self.face_analyser.get(img_data)
        try:
            largest = max(analysed, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
            return largest
        except:
            print("No face found")
            return None

    def predict(self, input_image, swap_image):
        """Run a single prediction on the model"""

        input_image_path = os.path.abspath(input_image)
        swap_image_path = os.path.abspath(swap_image)

        try:
            frame = cv2.imread(input_image_path)
            face = self.get_face(frame)
            source_face = self.get_face(cv2.imread(swap_image_path))
            # try:
            #     print(frame.shape, face.shape, source_face.shape)
            # except:
            #     print("printing shapes failed.")
            result = self.face_swapper.get(frame, face, source_face, paste_back=True)

            _, _, result = self.face_enhancer.enhance(
                result,
                paste_back=True
            )
            out_path = os.path.abspath(f"./images/temp/{str(int(time.time()))}.jpg")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            cv2.imwrite(out_path, result)
            return out_path
        except Exception as e:
            print(f"{e}")
            return None


# # Instantiate the Predictor class
# predictor = Predictor()
# title = "Swap Faces Using Our Model!!!"

# # Create Gradio Interface
# iface = gr.Interface(
#     fn=predictor.predict,
#     inputs=[
#         gr.inputs.Image(type="file", label="Target Image"),
#         gr.inputs.Image(type="file", label="Swap Image")
#     ],
#     outputs=gr.outputs.Image(type="file", label="Result"),
#     title=title,
#     examples=[["input.jpg", "swap img.jpg"]])


# # Launch the Gradio Interface
# iface.launch()
