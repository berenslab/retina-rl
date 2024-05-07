from typing import List
import os
import os.path as osp
import yaml
import argparse
import wandb
import random

from retinal_rl.util import resources_dir

### Directories ###

sweep_yaml_dir = osp.join(resources_dir, "sweep_yamls")


### Util ###


def merge_configs(configs: List[dict]) -> dict:
    merged_config = {}
    for config in configs:
        for key, value in config.items():
            if key == "parameters" and key in merged_config:
                merged_config[key].update(value)  # Merge parameters hierarchically
            else:
                merged_config[key] = value  # Replace other keys
    return merged_config


### Main ###


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description=f"""Utility to construct wandb sweeps for retinal-rl, by
        merging YAML files from the '{sweep_yaml_dir}' directory into
        a sweep. The first positional argument is the wandb group name, and
        the remaining arguments are the names of the component yaml files.
        """,
        epilog="""Example: python -m exec.compile-sweep mygroup gathering
            feedforward channels""",
    )
    parser.add_argument("wandb_group", type=str, help="wandb group name")
    parser.add_argument(
        "yaml_files", type=str, nargs="+", help="List of YAML configuration files"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Use analyze.py instead of train.py and set with_wandb to False",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="""Save the sweep configuration to a YAML file instead of uploading
            to wandb""",
    )
    parser.add_argument(
        "--trial",
        action="store_true",
        help="""Select random parameters from the sweep and print the command to
        run it""",
    )
    parser.add_argument(
        "--list_yamls",
        action="store_true",
        help="List available sweep yamls",
    )

    args = parser.parse_args()

    # Load and merge the YAML files
    configs: List[dict] = []
    for filename in args.yaml_files:
        with open(osp.join(sweep_yaml_dir, f"{filename}.yaml"), "r") as file:
            configs.append(yaml.safe_load(file))
    merged_config = merge_configs(configs)

    # Construct the job type variable
    wandb_job_type: str = "-".join(args.yaml_files)

    # Define the experiment variable
    experiment: str = "_".join(
        f"{param_name}-{{{param_name}}}"
        for param_name, param_info in merged_config["parameters"].items()
        if "values" in param_info
    )

    # Convert the merged config to a wandb sweep configuration
    sweep_config: dict = {
        "name": f"{args.wandb_group}-{wandb_job_type}",
        "project": merged_config["project"],
        "description": merged_config["description"],
        "method": merged_config["method"],
        "program": "-m exec.analyze" if args.analyze else "-m exec.train",
        "parameters": merged_config["parameters"],
    }

    # Update the wandb group, and set the experiment and job type
    sweep_config["parameters"].update(
        {
            "wandb_group": {"value": args.wandb_group},
            "wandb_job_type": {"value": wandb_job_type},
            "experiment": {"value": experiment},
            "train_dir": {"value": f"train_dir/{args.wandb_group}/{wandb_job_type}"},
        }
    )

    if args.list_yamls:
        print(f"Listing contents of {sweep_yaml_dir}:")
        for flnm in os.listdir(sweep_yaml_dir):
            print(flnm)
        return 0

    # If the --analyze flag is set, set with_wandb to False
    if args.analyze:
        sweep_config["parameters"]["with_wandb"] = {"value": False}

    if args.trial:
        # Select a random set of parameters
        trial_params = {
            name: random.choice(info["values"]) if "values" in info else info["value"]
            for name, info in sweep_config["parameters"].items()
        }
        command = " ".join(
            [f"--{name}={value}" for name, value in trial_params.items()]
        )
        print(f"python {sweep_config['program']} {command}")
    elif args.save:
        # If the --save flag is set, save the sweep configuration to a YAML file
        with open(f"{sweep_config['name']}.yaml", "w") as file:
            yaml.dump(sweep_config, file)
    else:
        # Otherwise, create a sweep
        sweep_id = wandb.sweep(sweep_config, project=merged_config["project"])
        print(f"Sweep ID: {sweep_id}")


if __name__ == "__main__":
    main()
