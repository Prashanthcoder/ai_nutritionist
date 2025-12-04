import random
from PIL import Image


def classify_food(image: Image.Image) -> tuple[str, float]:
    # dummy
    foods = ["pizza", "salad", "rice", "apple", "steak"]
    food = random.choice(foods)
    return food, round(random.uniform(0.75, 0.99), 2)
