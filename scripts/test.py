import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from best_results_set import *
import os
from itertools import chain

for f in os.listdir("images"):
    os.remove(os.path.join("images", f))

DIM = 3  # 2/3
np.random.seed(19680801)
brs = BestResultsSet(DIM, 4)
N = 101


def random_in_circle():
    while True:
        x = np.random.uniform(-1, 1)
        y = np.random.uniform(-1, 1)
        if DIM == 2:
            if x * x + y * y < 1:
                return x / 2 + 0.5, y / 2 + 0.5
        else:
            z = np.random.uniform(-1, 1)
            if x * x + y * y + z * z < 1:
                x *= 0.8
                y *= 1.1
                return x / 2 + 0.5, y / 2 + 0.5, z / 2 + 0.5


for i in range(N):
    print(i)
    for l in range(1):
        print(l)
        brs.add_all([(random_in_circle(), tuple(np.random.rand(1))) for e in range(5000)])
    if i % 10 == 0:
        brs.trim()
    data_copy = brs.data[:]


    best_data = set()
    for dim_weight in generate_one_distributions(brs.dimension_count, 10):
        best_data.update(brs.get_best(dim_weight))



    def get_color(d):
        is_best = d in best_data
        is_hull = False
        if is_best:
            if is_hull:
                return [0.7, 0, 0, 0.9]
            else:
                return [0, 0.6, 0, 0.8]
        else:
            if is_hull:
                return [0, 0.3, 0.8, 0.8]
            else:
                return [0, 0, 0, 0.5]


    colors = [get_color(d) for d in data_copy]
    x = [d[0][0] for d in data_copy]
    y = [d[0][1] for d in data_copy]
    if DIM == 2:
        plt.xlim([-0.1, 1.1])
        plt.ylim([-0.1, 1.1])
        plt.scatter(x, y, s=10, c=colors)
        plt.gcf().set_size_inches(3, 3)
    else:
        z = [d[0][2] for d in data_copy]
        fig = plt.figure()
        ax = Axes3D(fig)
        ax.view_init(elev=20, azim=135)
        ax.set_xlim3d(-0.1, 1.1)
        ax.set_ylim3d(-0.1, 1.1)
        ax.set_zlim3d(-0.1, 1.1)
        ax.plot(x, z, '+', c=[0, 0, 0, 0.25], zdir='y', zs=-0.1)
        ax.plot(y, z, '+', c=[0, 0, 0, 0.25], zdir='x', zs=1.1)
        ax.plot(x, y, '+', c=[0, 0, 0, 0.25], zdir='z', zs=-0.1)
        ax.scatter(x, y, z, s=50, c=colors)
        plt.gcf().set_size_inches(10, 10)
        k = 0
        for azim in chain(range(91, 180, 1), range(179, 91, -1)):
            k += 1
            ax.view_init(elev=20, azim=azim)
            plt.savefig('images/image_' + str(i).zfill(5) + "_" + str(k).zfill(3) + '.png')
        break
    plt.savefig('images/image_' + str(i).zfill(5) + '.png')
    plt.close()
