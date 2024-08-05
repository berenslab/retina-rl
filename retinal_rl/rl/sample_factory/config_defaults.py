from dataclasses import dataclass

@dataclass
class SfDefaults: #TODO: Identify model stuff and remove? Or just ignore? Overwrite if possible?
    # This block shouldn't be messed with without extensive testing
    ppo_clip_value=0.2
    obs_subtract_mean=0.0
    obs_scale=255.0
    env_frameskip=4
    # Environment defaults we've settled on
    res_h=120
    res_w=160
    decorrelate_envs_on_one_worker=False
    wide_aspect_ratio=False
    # Wandb stuff
    with_wandb="True"
    wandb_project="retinal-rl"
    wandb_group="free-range"
    wandb_job_type="test"
    # System specific but we'll still set these defaults
    train_for_env_steps=int(1e10)
    batch_size=2048
    num_workers=20
    num_envs_per_worker=8
    # All of these have been through some testing, and work as good defaults
    exploration_loss="symmetric_kl"
    exploration_loss_coeff=0.001
    with_vtrace=True
    normalize_returns=False
    normalize_input=True
    recurrence=32
    rollout=32
    use_rnn=False
    rnn_size=32
    # Evaluation-mode stuff
    eval_env_frameskip=1  # this is for smoother rendering during evaluation
    fps=35
    max_num_frames=1000
    max_num_episodes=100

    # Additional parameters in the config
    help = False
    algo = "APPO"
    env = "gathering_cifar"
    experiment = "gathering_Scifar_1"
    train_dir = "train_dir/complexity-complex-elu"
    restart_behavior = "resume"
    device = "gpu"
    seed = None
    num_policies = 1
    async_rl = True
    serial_mode = False
    batched_sampling = False
    num_batches_to_accumulate = 2
    worker_num_splits = 2
    policy_workers_per_policy = 1
    max_policy_lag = 1000
    num_batches_per_epoch = 1
    num_epochs = 1
    shuffle_minibatches = False
    gamma = 0.99
    reward_scale = 0.1
    reward_clip = 1000.0
    value_bootstrap = False
    value_loss_coeff = 0.5
    kl_loss_coeff = 0.0
    gae_lambda = 0.95
    ppo_clip_ratio = 0.1
    vtrace_rho = 1.0
    vtrace_c = 1.0
    optimizer = "adam"
    adam_eps = 1e-06
    adam_beta1 = 0.9
    adam_beta2 = 0.999
    max_grad_norm = 4.0
    learning_rate = 0.0001
    lr_schedule = "constant"
    lr_schedule_kl_threshold = 0.008
    normalize_input_keys = None
    decorrelate_experience_max_seconds = 0
    actor_worker_gpus = []
    set_workers_cpu_affinity = True
    force_envs_single_thread = False
    default_niceness = 0
    log_to_file = True
    experiment_summaries_interval = 10
    flush_summaries_interval = 30
    stats_avg = 100
    summaries_use_frameskip = True
    heartbeat_interval = 20
    heartbeat_reporting_interval = 180
    train_for_seconds = 10000000000
    save_every_sec = 120
    keep_checkpoints = 2
    load_checkpoint_kind = "latest"
    save_milestones_sec = -1
    save_best_every_sec = 5
    save_best_metric = "reward"
    save_best_after = 100000
    benchmark = False
    encoder_mlp_layers = [512, 512]
    encoder_conv_architecture = "convnet_simple"
    encoder_conv_mlp_layers = [512]
    rnn_type = "gru"
    rnn_num_layers = 1
    decoder_mlp_layers = []
    nonlinearity = "elu"
    policy_initialization = "orthogonal"
    policy_init_gain = 1.0
    actor_critic_share_weights = True
    adaptive_stddev = True
    continuous_tanh_scale = 0.0
    initial_stddev = 1.0
    use_env_info_cache = False
    env_gpu_actions = False
    env_gpu_observations = True
    env_framestack = 1
    pixel_format = "CHW"
    use_record_episode_statistics = False
    wandb_user = None
    wandb_tags = []
    with_pbt = False
    pbt_mix_policies_in_one_env = True
    pbt_period_env_steps = 5000000
    pbt_start_mutation = 20000000
    pbt_replace_fraction = 0.3
    pbt_mutation_rate = 0.15
    pbt_replace_reward_gap = 0.1
    pbt_replace_reward_gap_absolute = 1e-06
    pbt_optimize_gamma = False
    pbt_target_objective = "True_objective"
    pbt_perturb_min = 1.1
    pbt_perturb_max = 1.5
    num_agents = -1
    num_humans = 0
    num_bots = -1
    start_bot_difficulty = None
    timelimit = None
    global_channels = 16
    retinal_bottleneck = 4
    vvs_depth = 1
    kernel_size = 7
    retinal_stride = 2
    activation = "elu"
    greyscale = False
    repeat = 1
    wandb_unique_id = "gathering_cifar_1_20230304_005951_901407"
