from math import ceil, floor
from typing import List, Tuple, Union

import torch.nn as nn


def assert_list(
    list_candidate: Union[int, List[int]],
    len_list: int,
) -> List[int]:
    """Assert that the list has the expected length, or create a list of the same value repeated."""
    if isinstance(list_candidate, int):
        _list = [list_candidate] * len_list
    else:
        if len(list_candidate) != len_list:
            raise AssertionError(
                "The length of the list does not match the expected length: "
                + str(len(list_candidate))
                + " != "
                + str(len_list)
            )
        _list = list_candidate
    return _list


def encoder_out_size(mdls: List[nn.Module], hght0: int, wdth0: int) -> Tuple[int, int]:
    """Compute the size of the encoder output, where mdls is the list of encoder modules."""
    hght = hght0
    wdth = wdth0

    # iterate over modules that are not activations
    for mdl in mdls:
        if _is_activation(mdl):
            continue
        if not _is_convolutional_layer(mdl):
            raise NotImplementedError("Only convolutional layers are supported")

        krnsz = _double_up(mdl.kernel_size)
        strd = _double_up(mdl.stride)
        pad = _double_up(mdl.padding)
        dila = _double_up(mdl.dilation)

        if dila[0] != 1 or dila[1] != 1:
            raise NotImplementedError("Dilation not implemented")

        # if has a ceil mode
        if hasattr(mdl, "ceil_mode") and mdl.ceil_mode:
            hght = ceil((hght - krnsz[0] + 2 * pad[0]) / strd[0] + 1)
            wdth = ceil((wdth - krnsz[1] + 2 * pad[1]) / strd[1] + 1)
        else:
            hght = floor((hght - krnsz[0] + 2 * pad[0]) / strd[0] + 1)
            wdth = floor((wdth - krnsz[1] + 2 * pad[1]) / strd[1] + 1)

    return hght, wdth


def rf_size_and_start(mdls: List[nn.Module], hidx: int, widx: int):
    """Compute the receptive field size and start for each layer of the encoder, where mdls is the list of encoder modules."""
    hrf_size = 1
    hrf_scale = 1
    hrf_shift = 0

    wrf_size = 1
    wrf_scale = 1
    wrf_shift = 0

    hmn = hidx
    wmn = widx

    for mdl in mdls:
        if _is_activation(mdl):
            continue
        if not _is_convolutional_layer(mdl):
            raise NotImplementedError("Only convolutional layers are supported")

        hksz, wksz = _double_up(mdl.kernel_size)
        hstrd, wstrd = _double_up(mdl.stride)
        hpad, wpad = _double_up(mdl.padding)

        hrf_size += (hksz - 1) * hrf_scale
        wrf_size += (wksz - 1) * wrf_scale

        hrf_shift += hpad * hrf_scale
        wrf_shift += wpad * wrf_scale

        hrf_scale *= hstrd
        wrf_scale *= wstrd

        hmn = hidx * hrf_scale - hrf_shift
        wmn = widx * wrf_scale - wrf_shift

    return hrf_size, wrf_size, hmn, wmn


def _is_activation(mdl: nn.Module) -> bool:
    """Check if the module is an activation function."""
    return any(
        [
            isinstance(mdl, nn.ELU),
            isinstance(mdl, nn.ReLU),
            isinstance(mdl, nn.Tanh),
            isinstance(mdl, nn.Softplus),
            isinstance(mdl, nn.Identity),
        ]
    )


def _is_convolutional_layer(mdl: nn.Module) -> bool:
    return isinstance(mdl, (nn.Conv1d, nn.Conv2d, nn.Conv3d))


def _double_up(x: Union[int, List[int]]):
    if isinstance(x, int):
        return (x, x)
    return x
