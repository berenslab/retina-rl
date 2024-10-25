# Retinal RL

A deep learning framework for vision research using deep reinforcement learning.

## Apptainer Environment

### Installation

1. Install [Apptainer](https://apptainer.org/docs/user/latest/) to run the containerized environment.

2. Pull the pre-built container:
```bash
apptainer pull retinal-rl.sif oras://ghcr.io/berenslab/retinal-rl:singularity-image
```

Alternatively, build from source:
```bash
apptainer build retinal-rl.sif resources/retinal-rl.def
```

### Running Experiments

The scan command prints info about the proposed neural network architecture:
```bash
apptainer exec retinal-rl.sif python main.py +experiment="$experiment" command=scan
```
The experiment must always be specified with the `+experiment` flag. To train a
model, use the `train` command:
```bash
apptainer exec retinal-rl.sif python main.py +experiment="$experiment" command=train
```

`apptainer` commands can typically be replaced with `singularity` if the latter is rather used.

## Hydra Configuration

The project uses Hydra for configuration management.

### Directory Structure

The structure of the `./config/` directory is as follows:

```
base/config.yaml     # General and system configurations
user/
├── brain/           # Neural network architectures
├── dataset/         # Dataset configurations
├── optimizer/       # Training optimizers
└── experiment/      # Experiment configurations
```

Template configs are available under `./resources/config_templates/user/...`, which also provide documentation of the configuration variables themselves. Consult the hydra documentation for more information on [configuring your project](https://hydra.cc/docs/intro/).

### Default Configuration

1. Configuration templates may be copied to the user directory by running:
```bash
bash tests/ci/copy_configs.sh
```

2. Template and custom configurations can be sanity-checked with:
```bash
bash tests/ci/scan_configs.sh
```
which runs the `scan` command for all experiments.

## Weights & Biases Integration

### Basic Configuration

By default plots and analyses are saved locally. To enable Weights & Biases logging, add the `logging.use_wandb: True` flag to the command line:
```bash
apptainer exec retinal-rl.sif python main.py +experiment="$experiment" logging.use_wandb=True command=train
```

### Parameter Sweeps

[Wandb sweeps](https://docs.wandb.ai/guides/sweeps) can be added to
`user/sweeps/{sweep_name}.yaml` and launched from the command line:
```bash
apptainer exec retinal-rl.sif python main.py +experiment="$experiment" +sweep="$sweep" command=sweep
```

Typically the only command line arguments that need a `+` prefix will be `experiment` and `sweep`.
