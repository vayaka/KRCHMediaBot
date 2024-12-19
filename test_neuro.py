import onnxruntime
import torch
from app import Predictor

if __name__ == '__main__':
  print(onnxruntime.get_available_providers())
  print(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
