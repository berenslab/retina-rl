"""
retina_rl library

"""

from sample_factory.utils.utils import str2bool

from sf_examples.vizdoom.doom.doom_params import add_doom_env_args,add_doom_env_eval_args

def retinal_override_defaults(parser):
    """Overrides for the sample factory CLI defaults."""
    parser.set_defaults(
        # This block shouldn't be messed with without extensive testing
        ppo_clip_value=0.2,
        obs_subtract_mean=0.0,
        obs_scale=255.0,
        env_frameskip=4,
        reward_scale=0.1,

        # Environment defaults we've settled on
        res_h=90,
        res_w=120,
        wide_aspect_ratio=False,

        # Wandb stuff
        with_wandb='True',
        wandb_project="retinal-rl",
        wandb_group="free-range",
        wandb_job_type="test",

        # System specific but we'll still set these defaults
        batch_size=2048,
        num_workers=24,
        num_envs_per_worker=8,

        # All of these have been through some testing, and work as good defaults
        exploration_loss='symmetric_kl',
        exploration_loss_coeff=0.001,
        with_vtrace=True,
        normalize_returns=False,
        normalize_input=True,
        recurrence=32,
        rollout=32,
        use_rnn=False,
        rnn_size=64,

        # Evaluation-mode stuff
        eval_env_frameskip=1,  # this is for smoother rendering during evaluation
        fps=35,
        max_num_frames=1050,
        max_num_episodes=100,
    )

def add_retinal_env_args(parser):
    """
    Parse default SampleFactory arguments and add user-defined arguments on top.
    Allow to override argv for unit tests. Default value (None) means use sys.argv.
    Setting the evaluation flag to True adds additional CLI arguments for evaluating the policy (see the enjoy_ script).
    """

    # Doom args
    add_doom_env_args(parser)
    # Parse args for rvvs model from Lindsey et al 2019
    parser.add_argument('--global_channels', type=int, default=16, help='Standard number of channels in CNN layers')
    parser.add_argument('--retinal_bottleneck', type=int, default=4, help='Number of channels in retinal bottleneck')
    parser.add_argument('--vvs_depth', type=int, default=1, help='Number of CNN layers in the ventral stream network')
    parser.add_argument('--kernel_size', type=int, default=7, help='Size of CNN filters')
    parser.add_argument('--retinal_stride', type=int, default=2, help='Stride at the first conv layer (\'BC\'), doesnt apply to \'VVS\'')
    parser.add_argument( "--activation", default="relu" , choices=["elu", "relu", "tanh", "linear"]
                        , type=str, help="Type of activation function to use.")
    parser.add_argument('--repeat', type=int, default=1, help="Dummy parameter to indicate which repetition we're at in a wandb sweep")

def add_retinal_env_eval_args(parser):
    """
    Parse default SampleFactory arguments and add user-defined arguments on top.
    Allow to override argv for unit tests. Default value (None) means use sys.argv.
    Setting the evaluation flag to True adds additional CLI arguments for evaluating the policy (see the enjoy_ script).
    """

    # Doom args
    add_doom_env_eval_args(parser)

    parser.add_argument("--simulate", action="store_true", help="Runs simulations and analyses")
    parser.add_argument("--plot", action="store_true", help="Generate static plots")
    parser.add_argument("--animate", action="store_true", help="Animate 'analysis_out.npy'")
    parser.add_argument("--frame_step", type=int, default=0, help="Which frame of the animation to statically plot")
    parser.add_argument("--sta_repeats", type=int, default=10, help="Number of loops in generating STAs")
    #parser.add_argument('--analyze_acts', type=str, default='False', help='Visualize activations via gifs and dimensionality reduction; options: \'environment\', \'mnist\' or \'cifar\'')
    #parser.add_argument('--analyze_max_num_frames', type=int, default=1e3, help='Used for visualising \'environment\' activations (leave as default otherwise), normally 100000 works for a nice embedding, but can take time')
    #parser.add_argument('--analyze_ds_name', type=str, default='CIFAR', help='Used for visualizing responses to dataset (can be \'MNIST\' or \'CIFAR\'')
