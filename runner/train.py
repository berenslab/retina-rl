"""Training loop for the Brain."""

import logging
import time
from typing import Dict, List

import torch
from omegaconf import DictConfig
from torch.utils.data import DataLoader

import wandb
from retinal_rl.classification.objective import ClassificationContext
from retinal_rl.classification.training import process_dataset, run_epoch
from retinal_rl.dataset import Imageset
from retinal_rl.models.brain import Brain
from retinal_rl.models.optimizer import BrainOptimizer
from runner.analyze import analyze
from runner.util import save_checkpoint

# Initialize the logger
logger = logging.getLogger(__name__)


def train(
    cfg: DictConfig,
    device: torch.device,
    brain: Brain,
    brain_optimizer: BrainOptimizer[ClassificationContext],
    train_set: Imageset,
    test_set: Imageset,
    initial_epoch: int,
    history: Dict[str, List[float]],
):
    """Train the Brain model using the specified optimizer.

    Args:
    ----
        cfg (DictConfig): The configuration for the experiment.
        device (torch.device): The device to run the computations on.
        brain (Brain): The Brain model to train and evaluate.
        brain_optimizer (BrainOptimizer): The optimizer for updating the model parameters.
        train_set (Imageset): The training dataset.
        test_set (Imageset): The test dataset.
        initial_epoch (int): The epoch to start training from.
        history (Dict[str, List[float]]): The training history.

    """
    trainloader = DataLoader(train_set, batch_size=64, shuffle=True)
    testloader = DataLoader(test_set, batch_size=64, shuffle=False)

    wall_time = time.time()
    epoch_wall_time = 0

    if initial_epoch == 0:
        brain.train()
        train_losses = process_dataset(
            device, brain, brain_optimizer, initial_epoch, trainloader, is_training=False
        )
        brain.eval()
        test_losses = process_dataset(
            device, brain, brain_optimizer, initial_epoch, testloader, is_training=False
        )

        # Initialize the history
        for key in train_losses:
            history[f"train_{key}"] = [train_losses[key]]
        for key in test_losses:
            history[f"test_{key}"] = [test_losses[key]]

        analyze(
            cfg,
            device,
            brain,
            history,
            train_set,
            test_set,
            initial_epoch,
            True,
        )

        if cfg.use_wandb:
            _wandb_log_statistics(initial_epoch, epoch_wall_time, history)

    logger.info("Initialization complete.")

    for epoch in range(initial_epoch + 1, brain_optimizer.num_epochs() + 1):
        brain, history = run_epoch(
            device,
            brain,
            brain_optimizer,
            history,
            epoch,
            trainloader,
            testloader,
        )

        new_wall_time = time.time()
        epoch_wall_time = new_wall_time - wall_time
        wall_time = new_wall_time
        logger.info(f"Epoch {epoch} complete. Wall Time: {epoch_wall_time:.2f}s.")

        if epoch % cfg.system.checkpoint_step == 0:
            logger.info("Saving checkpoint and plots.")

            save_checkpoint(
                cfg.system.data_dir,
                cfg.system.checkpoint_dir,
                cfg.system.max_checkpoints,
                brain,
                brain_optimizer,
                history,
                epoch,
            )

            analyze(
                cfg,
                device,
                brain,
                history,
                train_set,
                test_set,
                epoch,
                True,
            )
            logger.info("Analysis complete.")

        if cfg.use_wandb:
            _wandb_log_statistics(epoch, epoch_wall_time, history)


def _wandb_log_statistics(
    epoch: int, epoch_wall_time: float, histories: Dict[str, List[float]]
) -> None:
    log_dict = {
        "Epoch": epoch,
        "Auxiliary/Epoch Wall Time": epoch_wall_time,
    }

    for key, values in histories.items():
        # Split the key into category (train/test) and metric name
        category, *metric_parts = key.split("_")
        metric_name = " ".join(word.capitalize() for word in metric_parts)

        # Create the full log key
        log_key = f"{category.capitalize()}/{metric_name}"

        # Add to log dictionary
        log_dict[log_key] = values[-1]

    wandb.log(log_dict, commit=True)
