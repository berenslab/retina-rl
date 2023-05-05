### Util for preparing simulations and data for analysis

import numpy as np
import torch
from math import floor

import os
from os.path import join

from sample_factory.algo.utils.make_env import BatchedVecEnv
from sample_factory.algo.utils.rl_utils import prepare_and_normalize_obs
from sample_factory.model.actor_critic import ActorCritic
from sample_factory.utils.typing import Config
from sample_factory.utils.utils import experiment_dir

from torch import nn


## Paths ###


def analysis_root(cfg):
    """
    Returns the root analysis directory.
    """

    return join(experiment_dir(cfg),"analyses")

def analysis_path(cfg,nstps):
    """
    Returns the path to the analysis directory.
    """
    art = analysis_root(cfg)

    return join(art,f"env_steps-{nstps}")

def get_analysis_times(cfg):
    """
    Returns the list of analysis times.
    """
    art = analysis_root(cfg)
    return [int(f.split("-")[1]) for f in os.listdir(art)]

def data_path(cfg,nstps,flnm=None):
    """
    Returns the path to the data directory.
    """

    datpth = analysis_path(cfg,nstps) + "/data"

    if flnm is not None:
        datpth = datpth + "/" + flnm

    return datpth

def plot_path(cfg,nstps,flnm=None):
    """
    Returns the path to the plot directory.
    """

    pltpth = analysis_path(cfg,nstps) + "/plots"

    if flnm is not None:
        pltpth = pltpth + "/" + flnm

    return pltpth


### IO ###


def save_onxx(cfg: Config, nstps : int, actor_critic : ActorCritic, env : BatchedVecEnv) -> None:
    """
    Write an onxx file of the saved model.
    """

    obs = env.observation_space.sample()
    normalized_obs = prepare_and_normalize_obs(actor_critic, obs)
    enc = actor_critic.encoder.basic_encoder
    obs = normalized_obs["obs"]
    # visualize obs only for the 1st agent

    # Note that onnx can't process dictionary inputs and so we can only look at the encoder (and decoder?) separately)
    torch.onnx.export(enc,torch.unsqueeze(obs,0),data_path(cfg,nstps,"encoder.onnx"),verbose=False,input_names=["observation"],output_names=["latent_state"])

def save_data(cfg : Config,nstps,dat,flnm):
    """
    Saves data. 'dat' should probably be a dictionary.
    """
    np.save(data_path(cfg,nstps,flnm), dat, allow_pickle=True)

def load_data(cfg : Config,nstps,flnm):
    """
    Loads data. Note the use of tolist() is necessary to read dictionaries.
    """
    return np.load(data_path(cfg,nstps,flnm) + ".npy", allow_pickle=True).tolist()


### Misc analysis tools ###

def normalize_data(xs):
    return (xs - np.min(xs)) / (np.max(xs) - np.min(xs))

def from_float_to_rgb(xs):
    return (255*normalize_data(xs)).astype(np.uint8)

def obs_dict_to_obs(obs_dct):
    """
    Extract observation
    """
    obs = obs_dct["obs"]
    # visualize obs only for the 1st agent
    return obs[0]


def obs_to_img(obs):
    """
    Rearrange an image so it can be presented by matplot lib.
    """
    # convert to HWC
    obs = obs.permute(1, 2, 0)
    # convert to numpy
    img = obs.cpu().numpy()
    return img


### Network Tools ###


def activation(act) -> nn.Module:
    if act == "elu":
        return nn.ELU(inplace=True)
    elif act == "relu":
        return nn.ReLU(inplace=True)
    elif act == "tanh":
        return nn.Tanh()
    elif act == "identity":
        return nn.Identity(inplace=True)
    else:
        raise Exception("Unknown activation function")

def is_activation(mdl: nn.Module) -> bool:
    bl = any([isinstance(mdl, nn.ELU)
        ,isinstance(mdl, nn.ReLU)
        ,isinstance(mdl, nn.Tanh)
        ,isinstance(mdl, nn.Identity)])
    return bl


def double_up(x):
    if isinstance(x,int): return (x,x)
    else: return x


def encoder_out_size(mdls,hght0,wdth0):
    """
    Compute the size of the encoder output, where mdls is the list of encoder
    modules.
    """

    hght = hght0
    wdth = wdth0

    # iterate over modules that are not activations
    for mdl in mdls:
        if is_activation(mdl): continue

        krnsz = double_up(mdl.kernel_size)
        strd = double_up(mdl.stride)
        pad = double_up(mdl.padding)
        # print geometry
        print(f"kernel size: {krnsz}")
        print(f"stride: {strd}")
        print(f"padding: {pad}")

        hght = floor((hght - krnsz[0] + 2*pad[0])/strd[0] + 1)
        wdth = floor((wdth - krnsz[1] + 2*pad[1])/strd[1] + 1)

    return hght,wdth

def rf_size_and_start(mdls,hidx,widx):
    """
    Compute the receptive field size and start for each layer of the encoder,
    where mdls is the list of encoder modules.
    """
    hrf_size = 1
    hrf_scale = 1
    hrf_start = 0

    wrf_size = 1
    wrf_scale = 1
    wrf_start = 0

    hmn = hidx
    wmn = widx

    for mdl in mdls:

        if is_activation(mdl): continue

        hksz,wksz = double_up(mdl.kernel_size)
        hstrd,wstrd = double_up(mdl.stride)
        hpad,wpad = double_up(mdl.padding)


        hrf_size += (hksz-1)*hrf_scale
        wrf_size += (wksz-1)*wrf_scale

        hrf_start += hpad*hrf_scale
        wrf_start += wpad*wrf_scale

        hrf_scale *= hstrd
        wrf_scale *= wstrd

        hmn=hidx*hrf_scale - hrf_start
        wmn=widx*wrf_scale - wrf_start

    return hrf_size,wrf_size,hmn,wmn


### Value Network ###


class ValueNetwork(nn.Module):

    """
    Converts a LindseyEncoder into a feedforward value network that can be easily analyzed by e.g. captum.
    """
    def __init__(self, cfg, actor_critic):

        super().__init__()

        self.cfg = cfg
        self.ac_base = actor_critic

        self.conv_head_out_size = actor_critic.encoder.basic_encoder.conv_head_out_size

        self.conv_head = actor_critic.encoder.basic_encoder.conv_head
        self.fc1 = actor_critic.encoder.basic_encoder.fc1 # here we will need to flatten the features before going forward
        self.nl_fc = actor_critic.encoder.basic_encoder.nl_fc

        self.critic = actor_critic.critic_linear


    def forward(self, nobs):
        # conv layer 1

        x = self.conv_head(nobs)
        x = x.contiguous().view(-1, self.conv_head_out_size)

        x = self.fc1(x)
        x = self.nl_fc(x)

        x = self.critic(x)

        return x
