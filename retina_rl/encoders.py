"""
retina_rl library

"""

from torch import nn

from sample_factory.algorithms.appo.model_utils import register_custom_encoder, EncoderBase, get_obs_shape, nonlinearity
from sample_factory.algorithms.utils.arguments import arg_parser, parse_args
from sample_factory.algorithms.utils.pytorch_utils import calc_num_elements
from sample_factory.run_algorithm import run_algorithm


class CNNEncoder(EncoderBase):

    def __init__(self, cfg, obs_space, timing):

        super().__init__(cfg, timing)

        obs_shape = get_obs_shape(obs_space)
        nchns = 16
        btlchnls = 4

        self.conv1 = nn.Conv2d(3, nchns, 9, stride=1)
        self.conv2 = nn.Conv2d(nchns, btlchnls, 9, stride=1)
        self.conv3 = nn.Conv2d(btlchnls, nchns, 9, stride=1)
        self.conv4 = nn.Conv2d(nchns, nchns, 9, stride=1)

        self.nl = nonlinearity(cfg)

        # Preparing Fully Connected Layers
        conv_layers = [
            self.conv1, self.nl,
            self.conv2, self.nl,
            self.conv3, self.nl,
            self.conv4, self.nl,
        ]

        self.conv_head = nn.Sequential(*conv_layers)
        self.conv_head_out_size = calc_num_elements(self.conv_head, obs_shape.obs)

        self.encoder_out_size = 512
        self.fc1 = nn.Linear(self.conv_head_out_size,self.encoder_out_size)

    def forward(self, x):
        # we always work with dictionary observations. Primary observation is available with the key 'obs'
        x = self.nl(self.conv1(x))
        x = self.nl(self.conv2(x))
        x = self.nl(self.conv3(x))
        x = self.nl(self.conv4(x))
        x = x.contiguous().view(-1, self.conv_head_out_size)
        x = self.nl(self.fc1(x))
        return x

class RNNEncoder(CNNEncoder):

    def __init__(self, cfg, obs_space,timing):

        super().__init__(cfg,obs_space,timing)
        self.cnn_encoder = CNNEncoder(cfg,obs_space,timing)

    def forward(self, obs_dict):
        # we always work with dictionary observations. Primary observation is available with the key 'obs'
        main_obs = obs_dict['obs']

        # forward pass through configurable fully connected blocks immediately after the encoder
        x = self.cnn_encoder(main_obs)
        return x

def register_custom_encoders():
    register_custom_encoder('retina_encoder', RNNEncoder)
