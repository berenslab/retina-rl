### Util for preparing simulations and data for analysis

from typing import Tuple

import numpy as np
import torch

from captum.attr import Saliency #, GuidedBackprop, Occlusion, IntegratedGradients, Deconvolution

from sample_factory.algo.learning.learner import Learner
from sample_factory.algo.sampling.batched_sampling import preprocess_actions
from sample_factory.algo.utils.action_distributions import argmax_actions
from sample_factory.algo.utils.make_env import make_env_func_batched,BatchedVecEnv
from sample_factory.algo.utils.rl_utils import prepare_and_normalize_obs
from sample_factory.algo.utils.tensor_utils import unsqueeze_tensor
from sample_factory.cfg.arguments import load_from_checkpoint
from sample_factory.model.actor_critic import create_actor_critic,ActorCritic
from sample_factory.model.model_utils import get_rnn_size
from sample_factory.utils.attr_dict import AttrDict
from sample_factory.utils.typing import Config
from sample_factory.algo.utils.env_info import extract_env_info

from retinal_rl.analysis.util import obs_dict_to_obs,obs_to_img,ValueNetwork,from_float_to_rgb

from tqdm.auto import tqdm

def get_ac_env(cfg: Config) -> Tuple[ActorCritic,BatchedVecEnv,AttrDict,int]:
    """
    Load the model from checkpoint, initialize the environment, and return both.
    """
    #verbose = False

    cfg = load_from_checkpoint(cfg)

    cfg.env_frameskip = cfg.eval_env_frameskip

    cfg.num_envs = 1

    # In general we only focus on saving to files
    render_mode = "rgb_array"

    env = make_env_func_batched(
        cfg, env_config=AttrDict(worker_index=0, vector_index=0, env_id=0), render_mode=render_mode
    )

    if hasattr(env.unwrapped, "reset_on_init"):
        # reset call ruins the demo recording for VizDoom
        env.unwrapped.reset_on_init = False

    actor_critic = create_actor_critic(cfg, env.observation_space, env.action_space)
    actor_critic.eval()

    device = torch.device("cpu" if cfg.device == "cpu" else "cuda")
    actor_critic.model_to_device(device)

    policy_id = cfg.policy_index
    name_prefix = dict(latest="checkpoint", best="best")[cfg.load_checkpoint_kind]
    checkpoints = Learner.get_checkpoints(Learner.checkpoint_dir(cfg, policy_id), f"{name_prefix}_*")
    checkpoint_dict = Learner.load_checkpoint(checkpoints, device)
    actor_critic.load_state_dict(checkpoint_dict["model"])
    nstps = checkpoint_dict["env_steps"]

    return actor_critic,env,cfg,nstps

def generate_simulation(cfg: Config, actor_critic : ActorCritic, env : BatchedVecEnv):
    """
    Save an example simulation.
    """

    # Initializing some local variables
    t_max = int(cfg.max_num_frames)
    env_info = extract_env_info(env, cfg)
    action_repeat: int = cfg.env_frameskip // cfg.eval_env_frameskip
    device = torch.device("cpu" if cfg.device == "cpu" else "cuda")
    valnet = ValueNetwork(cfg,actor_critic)
    att_method = Saliency(valnet)

    # Initializing stream arrays
    imgs = np.zeros((cfg.res_h, cfg.res_w, 3, t_max)).astype(np.uint8)
    nimgs = np.zeros((cfg.res_h, cfg.res_w, 3, t_max)).astype(np.uint8)
    attrs = np.zeros((cfg.res_h, cfg.res_w, 3, t_max)).astype(np.uint8)
    ltnts = np.zeros((cfg.rnn_size, t_max))
    acts = np.zeros((2, t_max))
    hlths = np.zeros(t_max)
    rwds = np.zeros(t_max)
    crwds = np.zeros(t_max)
    dns = np.zeros(t_max)

    # Initializing simulation state
    num_frames = 0
    obs_dict,_ = env.reset()
    nobs_dict = prepare_and_normalize_obs(actor_critic, obs_dict)
    rnn_states = torch.zeros([env.num_agents, get_rnn_size(cfg)], dtype=torch.float32, device=device)
    is_dn=0
    rwd=0
    crwd=0

    # Simulation loop
    with tqdm(total=t_max-1, desc="Generating Simulation") as pbar:

        while num_frames < t_max:

                # Evaluate policy
            policy_outputs = actor_critic(nobs_dict, rnn_states)
            rnn_states = policy_outputs["new_rnn_states"]
            actions = policy_outputs["actions"]

            # Prepare network state for saving
            ltnt = actor_critic.encoder(nobs_dict).cpu().detach().numpy()

            # can pass --eval_deterministic=True to CLI in order to argmax the probabilistic actions
            if cfg.eval_deterministic:
                action_distribution = actor_critic.action_distribution()
                actions = argmax_actions(action_distribution)

            # actions shape should be [num_agents, num_actions] even if it's [1, 1]
            if actions.ndim == 1:
                actions = unsqueeze_tensor(actions, dim=-1)
            actions = preprocess_actions(env_info, actions)

            # Repeating actions during evaluation because we run the simulation at higher FPS
            for _ in range(action_repeat):

                obs = obs_dict_to_obs(obs_dict)
                nobs = obs_dict_to_obs(nobs_dict)
                attr = att_method.attribute(nobs)

                img = obs_to_img(obs)
                nimg = obs_to_img(nobs)
                attrimg = obs_to_img(attr)

                health = env.unwrapped.get_info()['HEALTH'] # environment info (health etc.)

                if is_dn:
                    crwd=0
                else:
                    crwd+=rwd

                imgs[:,:,:,num_frames] = img
                nimgs[:,:,:,num_frames] = from_float_to_rgb(nimg)
                attrs[:,:,:,num_frames] = from_float_to_rgb(attrimg)
                ltnts[:,num_frames] = ltnt
                acts[:,num_frames] = actions
                hlths[num_frames] = health
                dns[num_frames] = is_dn
                rwds[num_frames] = rwd
                crwds[num_frames] = crwd

                obs_dict,rwd,terminated,truncated,_ = env.step(actions)
                is_dn = truncated | terminated
                nobs_dict = prepare_and_normalize_obs(actor_critic, obs_dict)
                actions = np.array(actions)

                num_frames += 1
                pbar.update(1)

                if num_frames >= t_max:
                    break

    return {
            "imgs": imgs,
            "nimgs": nimgs,
            "attrs": attrs,
            "ltnts": ltnts,
            "acts":acts,
            "hlths":hlths,
            "rwds":rwds,
            "crwds":crwds,
            "dns":dns,
            }



