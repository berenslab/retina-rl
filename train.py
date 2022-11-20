"""
From the root of Sample Factory repo this can be run as:
python -m sample_factory_examples.train_custom_env_custom_model --algo=APPO --env=my_custom_env_v1 --experiment=example --save_every_sec=5 --experiment_summaries_interval=10

After training for a desired period of time, evaluate the policy by running:
python -m sample_factory_examples.enjoy_custom_env_custom_model --algo=APPO --env=my_custom_env_v1 --experiment=example

"""

import sys
from retinal_rl.system.environment import register_retinal_environment
from retinal_rl.system.parameters import custom_parse_args
from retinal_rl.system.encoders import register_encoders

from sample_factory.run_algorithm import run_algorithm


def main():
    """Script entry point."""
    register_retinal_environment()
    register_encoders()
    cfg = custom_parse_args()
    status = run_algorithm(cfg)
    return status


if __name__ == '__main__':
    sys.exit(main())
