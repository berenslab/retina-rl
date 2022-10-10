# System
import sys
import os

# Numerics
import torch
import torchvision.datasets as datasets
from torch.utils.tensorboard import SummaryWriter
import numpy as np
from PIL import Image as im
# Sample Factory
from sample_factory.algorithms.appo.learner import LearnerWorker
from sample_factory.algorithms.utils.action_distributions import ContinuousActionDistribution
from sample_factory.algorithms.appo.model import create_actor_critic
from sample_factory.algorithms.utils.arguments import load_from_checkpoint
from sample_factory.algorithms.appo.model_utils import get_hidden_size
from sample_factory.envs.create_env import create_env
from sample_factory.utils.utils import log, AttrDict
from sample_factory.algorithms.appo.actor_worker import transform_dict_observations
from sample_factory.algorithms.utils.multi_agent_wrapper import MultiAgentWrapper

# Retinal-rl

from retinal_rl.environment import register_retinal_environment
from retinal_rl.parameters import custom_parse_args
from retinal_rl.encoders import register_encoders

# TODO: activations to gaussian noise input (move from visualization)

# TODO: activations to datasets (write based on jupyter notebook)

# activations during episodes of experience
def get_acts_environment(cfg, max_num_frames=1e3):

    render_action_repeat = cfg.render_action_repeat if cfg.render_action_repeat is not None else cfg.env_frameskip
    if render_action_repeat is None:
        log.warning('Not using action repeat!')
        render_action_repeat = 1
    log.debug('Using action repeat %d during evaluation', render_action_repeat)

    cfg.env_frameskip = 1  # for evaluation
    cfg.num_envs = 1

    def make_env_func(env_config):
        return create_env(cfg.env, cfg=cfg, env_config=env_config)

    env = make_env_func(AttrDict({'worker_index': 0, 'vector_index': 0}))
    env = MultiAgentWrapper(env)
    # env.seed(0)

    if hasattr(env.unwrapped, 'reset_on_init'):
        # reset call ruins the demo recording for VizDoom
        env.unwrapped.reset_on_init = False

    actor_critic = create_actor_critic(cfg, env.observation_space, env.action_space)

    device = torch.device('cpu' if cfg.device == 'cpu' else 'cuda')
    actor_critic.model_to_device(device)

    policy_id = cfg.policy_index
    checkpoints = LearnerWorker.get_checkpoints(LearnerWorker.checkpoint_dir(cfg, policy_id))
    checkpoint_dict = LearnerWorker.load_checkpoint(checkpoints, device)
    actor_critic.load_state_dict(checkpoint_dict['model'])

    num_frames = 0

    def max_frames_reached(frames):
        return max_num_frames is not None and frames > max_num_frames

    ### Parsing out the encoder and preparing some analyses

    enc = actor_critic.encoder.base_encoder

    obs = env.reset()
    print("\nEnvironment Info:")
    print(env.unwrapped.get_info())
    obs_torch = AttrDict(transform_dict_observations(obs))
    for key, x in obs_torch.items():
        obs_torch[key] = torch.from_numpy(x).to(device).float()

    ### Analysing encoder
    print("\nActor-Critic Stats:")
    print(actor_critic)
    # Printing encoder stats
    print("\nEncoder-Stats:")
    print(enc)
    
    # logging comp graph to tensorboard
    tb_path = cfg.train_dir +  "/" + cfg.experiment + '/.summary/0/'
    writer = SummaryWriter(tb_path)
    writer.add_graph(enc, obs_torch['obs'])
    writer.close()


    n_conv_lay = len(enc.conv_head)//2 # sequential list


    ### Running and saving a simulation

    img0 = obs_torch['obs'][0,:,:,:]
    imgs = [np.transpose(img0.cpu().detach().numpy(),(1,2,0)).astype(np.uint8)]
    conv_acts = [ [] for _ in range(n_conv_lay) ]
    fc_acts = []
    rnn_acts = []
    v_acts = []
    rnn_states = torch.zeros([env.num_agents, get_hidden_size(cfg)], dtype=torch.float32, device=device)
    env_infos = []


    with torch.no_grad():

        while not max_frames_reached(num_frames):
            
            # track progress
            if num_frames % int(max_num_frames/20) == 0:
                print(f'Simulated {num_frames} / {int(max_num_frames)} environment steps.')

            policy_outputs = actor_critic(obs_torch, rnn_states, with_action_distribution=True)

            # sample actions from the distribution by default
            actions = policy_outputs.actions

            action_distribution = policy_outputs.action_distribution
            if isinstance(action_distribution, ContinuousActionDistribution):
                if not cfg.continuous_actions_sample:  # TODO: add similar option for discrete actions
                    actions = action_distribution.means

            actions = actions.cpu().numpy()

            rnn_states = policy_outputs.rnn_states

            for _ in range(render_action_repeat):

                obs,_,_,_ = env.step(actions)
                obs_torch = AttrDict(transform_dict_observations(obs))
                for key, x in obs_torch.items():
                    obs_torch[key] = torch.from_numpy(x).to(device).float()

                img0 = obs_torch['obs'][0,:,:,:] # activation of input layer (=pixels)
                img = np.transpose(img0.cpu().detach().numpy(),(1,2,0)).astype(np.uint8)
                imgs.append(img)

                for lay in range(1,n_conv_lay+1):
                    conv_act_torch = enc.conv_head[0:(lay*2)](obs_torch['obs'])[0,:,:,:].permute(1, 2, 0) # activation of intermediate conv layers
                    conv_act_np = conv_act_torch.cpu().detach().numpy()
                    conv_acts[lay-1].append(conv_act_np)

                fc_act_torch = enc.forward(obs_torch['obs']) # activation of output fc layer
                fc_act_np = fc_act_torch.cpu().detach().numpy()
                fc_acts.append(fc_act_np)
                env_infos.append(env.unwrapped.get_info()) # to get health and coordinates
                rnn_act_torch = policy_outputs.rnn_states
                rnn_acts_np = rnn_act_torch.cpu().detach().numpy()
                rnn_acts.append(rnn_acts_np) # to get rnn 'hidden state'
                v_act = actor_critic.critic_linear(policy_outputs.rnn_states) # forward pass of hidden state to get value
                v_act_np = v_act.cpu().detach().numpy()
                v_acts.append(v_act_np)
                num_frames += 1

    pix_acts = [imgs[i].flatten()[None,:] for i in range(len(imgs)-1)] # for embedding

    env.close()
    
    # saving all of these in a dictionary

    all_acts_dict = {'obs_torch':obs_torch, 'imgs':imgs, 'pix_acts':pix_acts, 'conv_acts' : conv_acts, 'fc_acts' : fc_acts, 'rnn_acts':rnn_acts, 'v_acts':v_acts}

    return (enc, env_infos, all_acts_dict)


def get_acts_dataset(cfg, actor_critic):

    bck_np = np.load(os.getcwd() + '/data/doom_pad.npy') # saved 'doom-looking' background
    
    if cfg.analyze_ds_name == 'CIFAR':
        trainset = datasets.CIFAR10(root='./data', train=True, download=True, transform=None)
        testset = datasets.CIFAR10(root='./data', train=False, download=True, transform=None)
        rewards_dict = {0:2, 1:1, 2:4, 3:5, 4:7, 5:6, 6:8, 7:9, 8:3, 9:0} # defined by the class-reward assignments in the .wad file

    elif cfg.analyze_ds_name == 'MNIST':
        trainset = datasets.MNIST(root='./data', train=True, download=True, transform=None)
        testset = datasets.MNIST(root='./data', train=False, download=True, transform=None)
        rewards_dict = {0:0, 1:1, 2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8, 9:9} # defined by the class-reward assignments in the .wad file (matching digits in case of mnist)

    n_stim = len(trainset)
    offset = (28,50)

    all_fc_act = np.zeros((cfg.hidden_size, n_stim))
    all_img = np.zeros((cfg.res_h, cfg.res_w, 3, n_stim))
    all_lab = np.zeros(n_stim)

    with torch.no_grad():
        for i in range(n_stim):
                obs = pad_dataset(cfg, i, trainset, bck_np, offset)
                fc_act_torch = actor_critic.encoder.base_encoder.forward(obs) # activation of output fc layer
                
                all_fc_act[:,i] = fc_act_torch.cpu().detach().numpy()
                all_img[:,:,:,i] = obs_to_img(obs).astype(np.uint8)
                all_lab[i] = rewards_dict[trainset[i][1]] # getting label for sample and converting based on health assignment    

                # progress
                if i % int(n_stim/20) == 0:
                    print(f'Forward pass through {i}/{n_stim} dataset entries')

    analyze_ds_out = {'all_img': all_img,
                    'all_fc_act':all_fc_act,
                   'all_lab':all_lab}
    
    return analyze_ds_out


def obs_to_img(obs):
    img = np.array(obs[0].cpu()).astype(np.uint8)
    img = np.transpose(img, (1,2,0))
    return img


def pad_dataset(cfg, i, trainset, bck_np, offset): # i:index in dataset, bck_np: numpy array of background (grass/sky), offset:determines position within background
    device = torch.device('cpu' if cfg.device == 'cpu' else 'cuda')
    in_im = trainset[i][0]
    in_np = np.array(np.transpose(in_im, (2,0,1)))
    out_np = bck_np # background
    out_np[:,offset[0]:offset[0]+32, offset[1]:offset[1]+32]=in_np # replacing pixels in the middle
    out_np_t =np.transpose(out_np, (1, 2, 0)) # reformatting for PIL conversion
    out_im = im.fromarray(out_np_t)
    out_torch = torch.from_numpy(out_np[None,:,:,:]).float().to(device) 
    
    return out_torch # same format as obs_torch['obs']