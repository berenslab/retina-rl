"""Objectives for training models."""

from typing import Dict, List, Tuple

import torch
import torch.nn as nn
from torch import Tensor

from retinal_rl.models.brain import Brain
from retinal_rl.models.loss import BaseContext, Loss


class ClassificationContext(BaseContext):
    """Context class for classification tasks.

    This class extends BaseContext with attributes specific to classification problems.

    Attributes
    ----------
        inputs (Tensor): The input data for the classification task.
        classes (Tensor): The true class labels for the input data.

    """

    def __init__(
        self,
        sources: Tensor,
        inputs: Tensor,
        classes: Tensor,
        responses: Dict[str, Tensor],
        epoch: int,
    ):
        """Initialize the classification context object."""
        super().__init__(sources, inputs, responses, epoch)
        self.classes = classes


class ClassificationLoss(Loss[ClassificationContext]):
    """Loss for computing the cross entropy loss."""

    def __init__(
        self,
        min_epoch: int = 0,
        max_epoch: int = -1,
        target_circuits: List[str] = [],
        weights: List[float] = [],
    ):
        """Initialize the classification loss."""
        super().__init__(min_epoch, max_epoch, target_circuits, weights)
        self.loss_fn = nn.CrossEntropyLoss()

    def compute_value(self, context: ClassificationContext) -> Tensor:
        """Compute the cross entropy loss between the predictions and the targets."""
        predictions = context.responses["classifier"]
        classes = context.classes

        if predictions.shape[0] != classes.shape[0]:
            raise ValueError(
                f"Shape mismatch: predictions {predictions.shape}, classes {classes.shape}"
            )

        return self.loss_fn(predictions, classes)


class PercentCorrect(Loss[ClassificationContext]):
    """(Inverse) Loss for computing the percent correct classification."""

    def __init__(
        self,
        min_epoch: int = 0,
        max_epoch: int = -1,
        target_circuits: List[str] = [],
        weights: List[float] = [],
    ):
        super().__init__(min_epoch, max_epoch, target_circuits, weights)

    def compute_value(self, context: ClassificationContext) -> Tensor:
        """Compute the percent correct classification."""
        predictions = context.responses["classifier"]
        classes = context.classes
        if predictions.shape[0] != classes.shape[0]:
            raise ValueError(
                f"Shape mismatch: predictions {predictions.shape}, classes {classes.shape}"
            )
        predicted = torch.argmax(predictions, dim=1)
        correct = (predicted == classes).sum()
        total = torch.tensor(classes.size(0))
        return correct / total


def get_classification_context(
    device: torch.device,
    brain: Brain,
    batch: Tuple[torch.Tensor, torch.Tensor, torch.Tensor],
    epoch: int,
) -> ClassificationContext:
    """Calculate the loss dictionary for a single batch.

    This function processes a single batch of data through the Brain model and prepares
    a context dictionary for the optimizer to calculate losses.

    Args:
    ----
        device (torch.device): The device to run the computations on.
        brain (Brain): The Brain model to process the data.
        epoch (int): The current epoch number.
        batch (Tuple[torch.Tensor, torch.Tensor]): A tuple containing input data and labels.

    Returns:
    -------
        Dict[str, torch.Tensor]: A context dictionary containing all necessary information
                                 for loss calculation and optimization.

    """
    sources, inputs, classes = batch
    sources, inputs, classes = sources.to(device), inputs.to(device), classes.to(device)

    stimuli = {"vision": inputs}
    responses = brain(stimuli)

    return ClassificationContext(
        sources=sources,
        inputs=inputs,
        classes=classes,
        responses=responses,
        epoch=epoch,
    )
