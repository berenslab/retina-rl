import os
import shutil
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import torch
import wandb
from matplotlib.figure import Figure
from omegaconf import DictConfig
from torch import Tensor
from torch.utils.data import Dataset

from retinal_rl.classification.plot import (
    plot_input_distributions,
    plot_training_histories,
)
from retinal_rl.models.analysis.plot import plot_reconstructions, receptive_field_plots
from retinal_rl.models.analysis.statistics import (
    get_reconstructions,
    gradient_receptive_fields,
)
from retinal_rl.models.brain import Brain

FigureDict = Dict[str, Figure]


def analyze(
    cfg: DictConfig,
    device: torch.device,
    brain: Brain,
    histories: Dict[str, List[float]],
    train_set: Dataset[Tuple[Tensor, int]],
    test_set: Dataset[Tuple[Tensor, int]],
    epoch: int,
    copy_checkpoint: bool = False,
):
    fig_dict: FigureDict = {}

    # Plot training histories
    if not cfg.logging.use_wandb:
        hist_fig = plot_training_histories(histories)
        fig_dict["training-histories"] = hist_fig

    # Plot input distributions if required
    if cfg.command.plot_inputs:
        rgb_fig = plot_input_distributions(train_set)
        fig_dict["input-distributions"] = rgb_fig

    # Plot receptive fields
    rf_dict = gradient_receptive_fields(device, brain.circuits["encoder"])
    for lyr, rfs in rf_dict.items():
        rf_fig = receptive_field_plots(rfs)
        fig_dict[f"receptive-fields/{lyr}-layer"] = rf_fig

    # Plot reconstructions
    rec_dict = get_reconstructions(device, brain, train_set, test_set, 5)
    recon_fig = plot_reconstructions(**rec_dict, num_samples=5)
    fig_dict["reconstructions"] = recon_fig

    # Handle logging or saving of figures
    if cfg.logging.use_wandb:
        _log_figures(fig_dict, epoch)
    else:
        _save_figures(cfg, epoch, fig_dict, copy_checkpoint)


def _wandb_title(title: str) -> str:
    # Split the title by slashes
    parts = title.split("/")

    def capitalize_part(part: str) -> str:
        # Split the part by dashes
        words = part.split("-")
        # Capitalize each word
        capitalized_words = [word.capitalize() for word in words]
        # Join the words with spaces
        return " ".join(capitalized_words)

    # Capitalize each part, then join with slashes
    capitalized_parts = [capitalize_part(part) for part in parts]
    return "/".join(capitalized_parts)


def _log_figures(fig_dict: FigureDict, epoch: int) -> None:
    """Log figures to wandb."""
    fig_dict_prefixed = {
        f"Figures/{_wandb_title(key)}": fig for key, fig in fig_dict.items()
    }
    wandb.log(fig_dict_prefixed, step=epoch, commit=False)

    # Close the figures to free up memory
    for fig in fig_dict.values():
        plt.close(fig)


def _save_figures(
    cfg: DictConfig, epoch: int, fig_dict: FigureDict, copy_checkpoint: bool
):
    plot_path = cfg.system.plot_path
    os.makedirs(plot_path, exist_ok=True)

    for key, fig in fig_dict.items():
        fig_path = key.replace("/", os.sep)
        full_path = os.path.join(plot_path, fig_path + ".png")
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        fig.savefig(full_path)
        plt.close(fig)

    if copy_checkpoint:
        checkpoint_plot_path = (
            f"{cfg.system.checkpoint_plot_path}/checkpoint-epoch-{epoch}"
        )
        os.makedirs(checkpoint_plot_path, exist_ok=True)

        # Copy 'receptive-fields' directory
        src_dir = os.path.join(plot_path, "receptive-fields")
        dst_dir = os.path.join(checkpoint_plot_path, "receptive-fields")
        if os.path.exists(src_dir):
            shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

        # Copy 'reconstructions.png' file
        src_file = os.path.join(plot_path, "reconstructions.png")
        dst_file = os.path.join(checkpoint_plot_path, "reconstructions.png")
        if os.path.exists(src_file):
            os.makedirs(checkpoint_plot_path, exist_ok=True)
            shutil.copy2(src_file, dst_file)
