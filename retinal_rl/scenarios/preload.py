import os
import shutil

from num2words import num2words
import os.path as osp

from torchvision.datasets import MNIST
from torchvision.datasets import CIFAR10
from torchvision.datasets import CIFAR100


### Loading Datasets ###


def preload_apples():
    # check if resources/textures/apples exists
    if not osp.exists("resources/textures/apples"):
        # and copy apple images from resources/base
        shutil.copytree("resources/base/apples","resources/textures/apples")

def preload_mnist():
    # check if resources/textures/mnist exists
    if not osp.exists("resources/textures/mnist"):
    # if not, create it
        os.makedirs("resources/textures/mnist")
    # download mnist images
        mnist = MNIST("resources/textures/mnist", download=True)
    # save mnist images as pngs organized by word label
        for i in range(10):
            os.makedirs("resources/textures/mnist/" + num2words(i))
        for i in range(len(mnist)):
            mnist[i][0].save("resources/textures/mnist/" + num2words(mnist[i][1]) + "/" + str(i) + ".png")

        # remove all downloaded data except for the pngs
        shutil.rmtree("resources/textures/mnist/MNIST", ignore_errors=True)

    else:
        print("mnist dir exists, files not downloaded)")

def preload_cifar10():
    # check if resources/textures/cifar-10 exists
    if not osp.exists("resources/textures/cifar-10"):
        # if not, create it
        os.makedirs("resources/textures/cifar-10")
        # download cifar images
        cifar = CIFAR10("resources/textures/cifar-10", download=True)
        # save cifar images as pngs organized by label name
        for i in range(10):
            os.makedirs("resources/textures/cifar-10/" + cifar.classes[i])
        for i in range(len(cifar)):
            cifar[i][0].save("resources/textures/cifar-10/" + cifar.classes[cifar[i][1]] + "/" + str(i) + ".png")

        # remove all downloaded data except for the pngs
        os.remove("resources/textures/cifar-10/cifar-10-python.tar.gz")
        shutil.rmtree("resources/textures/cifar-10/cifar-10-batches-py", ignore_errors=True)
    else:
        print("cifar-10 dir exists, files not downloaded")

def preload_cifar100():
    # check if resources/textures/cifar-100 exists
    if not osp.exists("resources/textures/cifar-100"):
        # if not, create it
        os.makedirs("resources/textures/cifar-100")
        # download cifar images
        cifar = CIFAR100("resources/textures/cifar-100", download=True)
        # save cifar images as pngs organized by label name
        for i in range(100):
            os.makedirs("resources/textures/cifar-100/" + cifar.classes[i])
        for i in range(len(cifar)):
            cifar[i][0].save("resources/textures/cifar-100/" + cifar.classes[cifar[i][1]] + "/" + str(i) + ".png")

        # remove all downloaded data except for the pngs
        os.remove("resources/textures/cifar-100/cifar-100-python.tar.gz")
        shutil.rmtree("resources/textures/cifar-100/cifar-100-python", ignore_errors=True)
    else:
        print("cifar-100 dir exists, files not downloaded")
