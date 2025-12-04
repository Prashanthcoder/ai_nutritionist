import random
from PIL import Image


def predict_weight(image: Image.Image) -> float:
    # dummy: random 50-500 g
    return round(random.uniform(50, 500), 1)
