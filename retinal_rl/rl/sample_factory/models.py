from typing import Dict, Optional
from sample_factory.model.actor_critic import ActorCritic
from sample_factory.model.encoder import Encoder
from sample_factory.model.decoder import Decoder
from sample_factory.model.core import ModelCore
from sample_factory.utils.typing import ActionSpace, Config, ObsSpace
from sample_factory.algo.utils.context import global_model_factory
from sample_factory.algo.utils.tensor_dict import TensorDict
from torch import Tensor
import torch
import numpy as np
import networkx as nx
from retinal_rl.models.brain import Brain
from retinal_rl.rl.interface import BrainInterface
from retinal_rl.rl.sample_factory.sf_interfaces import ActorCriticProtocol
import warnings
from enum import Enum
from torch import nn

class CoreMode(Enum):
    IDENTITY = 0,
    SIMPLE = 1,
    RNN = 2,
    MULTI_MODULES = 3,


class SampleFactoryBrain(ActorCritic, ActorCriticProtocol, BrainInterface):
    def __init__(self, obs_space: ObsSpace, action_space: ActionSpace, cfg: Config):
        super().__init__(obs_space, action_space, cfg)

        self.set_brain(Brain(**cfg.brain)) # TODO: Find way to instantiate brain outside

        dec_out_shape = self.brain.circuits[self.decoder_name].output_shape
        decoder_out_size = np.prod(dec_out_shape)
        self.critic_linear = nn.Linear(decoder_out_size, 1)
        self.action_parameterization = self.get_action_parameterization(decoder_out_size)

    def set_brain(self, brain: Brain):
        """
        method to set weights / brain.
        Checks for brain compatibility.
        Decide which part of the brain is head/core/tail or creates Identity transforms if needed.
        """
        enc, core, dec = self.get_encoder_decoder(brain)
        self.brain = brain
        self.encoder_name = enc
        self.decoder_name = dec
        self.core_mode = core


    @staticmethod
    def get_encoder_decoder(brain: Brain):
        assert "vision" in brain.sensors.keys() # needed as input
        # potential TODO: add other input sources if needed?

        vision_paths = []
        for node in brain.connectome:
            if brain.connectome.out_degree(node)==0: #it's a leaf
                vision_paths.append(nx.shortest_path(brain.connectome, "vision", node))

        decoder = "action_decoder" # default assumption
        if decoder in brain.circuits.keys(): # needed to produce output = decoder
            vision_path = nx.shortest_path(brain.connectome, "vision", "action_decoder")
        else:
            vision_path = vision_paths[0]
            decoder = vision_path[-1]
            warnings.warn("No action decoder in model. Will use " + decoder + " instead.")

        encoder = vision_path[1]
        if len(vision_path) == 4:
            core = CoreMode.SIMPLE
            CoreMode.SIMPLE.value = vision_path[2] # use center module as core
            #TODO: Check if recurrent!
        if len(vision_path) < 4:
            core = CoreMode.IDENTITY
            warnings.warn("Seems like there is no model core. Will use an Identity.")
        else: # more than four
            core = CoreMode.MULTI_MODULES
            warnings.warn("Will use multiple modules as core: " + ', '.join([mod_name for mod_name in vision_path[2:-1]]) )

        return encoder, core, decoder

    def forward_head(self, normalized_obs_dict: Dict[str, Tensor]) -> Tensor:
        vision_input = normalized_obs_dict["obs"]
        return self.brain.circuits[self.encoder_name](vision_input)

    def forward_core(self, head_output, rnn_states):
        #TODO: what to do with rnn states?
        if self.core_mode == CoreMode.SIMPLE:
            out = self.brain.circuits[self.core_mode.value](head_output)
        elif self.core_mode == CoreMode.RNN:
            out, rnn_states = self.brain.circuits[self.core_mode.value](head_output, rnn_states)
        elif self.core_mode == CoreMode.IDENTITY:
            out = head_output
        if self.core_mode == CoreMode.MULTI_MODULES:
            out = head_output #TODO: Implement partial forward (in brain!)
        return out, rnn_states

    def forward_tail(
        self, core_output, values_only: bool, sample_actions: bool
    ) -> TensorDict:
        out = self.brain.circuits[self.decoder_name](core_output)
        out = torch.flatten(out, 1)

        values = self.critic_linear(out).squeeze()

        result = TensorDict(values=values)
        if values_only:
            return result

        action_distribution_params, self.last_action_distribution = self.action_parameterization(out)

        # `action_logits` is not the best name here, better would be "action distribution parameters"
        result["action_logits"] = action_distribution_params

        self._maybe_sample_actions(sample_actions, result)
        return result


    def forward(
        self, normalized_obs_dict, rnn_states, values_only: bool = False
    ) -> TensorDict:
        head_out = self.forward_head(normalized_obs_dict)
        core_out, new_rnn_states = self.forward_core(head_out, rnn_states)
        result = self.forward_tail(core_out, values_only=values_only, sample_actions=True)
        result["new_rnn_states"] = new_rnn_states
        result["latent_states"] = core_out
        return result


    def get_brain(self) -> Brain:
        return self.brain
