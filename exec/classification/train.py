### Imports ###

import torch
from torchvision.datasets import CIFAR10
from torchvision.transforms import transforms

import hydra
from omegaconf import DictConfig

from retinal_rl.classification.training import cross_validate, save_results

@hydra.main(config_path="../../resources/config", config_name="classification", version_base=None)
def train(cfg: DictConfig):

    # Load CIFAR-10 dataset
    transform = transforms.Compose(
        [transforms.ToTensor(), transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))]
    )
    dataset = CIFAR10(root="./cache", train=True, download=True, transform=transform)

    # Run cross-validation
    models, histories = cross_validate(
        torch.device(cfg.device),
        cfg.brain,
        cfg.num_folds,
        cfg.num_epochs,
        cfg.recon_weight,
        dataset,
    )

    # Save results
    save_results(models, histories, cfg.train_dir, cfg.recon_weight)


if __name__ == "__main__":
    train()
