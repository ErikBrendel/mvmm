import random

from util import *

for i in range(1000):
    data = list(range(random.randrange(100, 5000)))
    random.shuffle(data)
    indices = random.sample(list(range(len(data))), random.randrange(0, len(data)))
    manual_result = [x for i, x in enumerate(data) if i not in indices]
    remove_indices(data, indices)
    print(len(manual_result) == len(data))
    print(set(manual_result) == set(data))
