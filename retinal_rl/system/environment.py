import os
from os.path import join
import functools

from sample_factory.envs.env_utils import register_env

from sf_examples.vizdoom.doom.doom_utils import DoomSpec, make_doom_env_impl

import gym
from gym.spaces import Discrete



### Action Spaces ###


def key_to_action_basic(key):
    from pynput.keyboard import Key

    table = {Key.left: 0, Key.right: 1, Key.up: 2, Key.down: 3}
    return table.get(key, None)

def doom_action_space_basic():
    """
    TURN_LEFT
    TURN_RIGHT
    MOVE_FORWARD
    MOVE_BACKWARD
    """
    space = gym.spaces.Tuple(
        (
            Discrete(3),
            Discrete(3),
        )
    )  # noop, turn left, turn right  # noop, forward, backward

    space.key_to_action = key_to_action_basic
    return space

### Retinal AlgoObserver ###

### Retinal Environments ###

def retinal_doomspec(scnr,flnm):
    return DoomSpec( scnr
                    , join(os.getcwd(), "scenarios", flnm)
                    , doom_action_space_basic()
                    , reward_scaling=0.01
                    , extra_wrappers=[]
                    )

RETINAL_ENVS = [

    retinal_doomspec("gathering_cifar", "cifar_gathering_01.cfg"),
    retinal_doomspec("gathering_gabors", "gabor_gathering_02.cfg"),
    retinal_doomspec("gathering_apples", "apple_gathering_02.cfg"),
    retinal_doomspec("gathering_mnist", "mnist_gathering_01.cfg"),
    retinal_doomspec("appmnist_apples", "appmnist_apples_gathering_01.cfg"),
    retinal_doomspec("appmnist_mnist", "appmnist_mnist_gathering_01.cfg")

]


def make_retinal_env_from_spec(spec, _env_name, cfg, env_config, render_mode: Optional[str] = None, **kwargs):
    """
    Makes a Doom environment from a DoomSpec instance.
    _env_name is unused but we keep it, so functools.partial(make_doom_env_from_spec, env_spec) can registered
    in Sample Factory (first argument in make_env_func is expected to be the env_name).
    """

    make_doom_env_impl(spec, cfg=cfg, env_config=env_config, render_mode=render_mode, custom_resolution=cfg.resolution, **kwargs)

def register_retinal_envs():
    for env_spec in RETINAL_ENVS:
        make_env_func = functools.partial(make_retinal_env_from_spec, env_spec)
        register_env(env_spec.name, make_env_func)
