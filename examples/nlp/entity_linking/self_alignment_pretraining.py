# Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
## Task

## Preparing the dataset

## Model Training
"""

from pytorch_lightning import Trainer
from omegaconf import DictConfig, OmegaConf

from nemo.collections.nlp.models import EntityLinkingModel
from nemo.core.config import hydra_runner
from nemo.utils import logging
from nemo.utils.exp_manager import exp_manager

@hydra_runner(config_path="conf", config_name="augmented_medical_entity_linking_config.yaml")
def main(cfg: DictConfig) -> None:
    logging.info(f"\nConfig Params:\n{cfg.pretty()}")
    trainer = Trainer(**cfg.trainer)
    exp_manager(trainer, cfg.get("exp_manager", None))

    logging.info(f"Loading weights from pretrained model {cfg.model.language_model.pretrained_model_name}")
    model = EntityLinkingModel(cfg=cfg.model, trainer=trainer)
    logging.info("===========================================================================================")
    logging.info('Starting training...')
    trainer.fit(model)
    logging.info('Training finished!')
    logging.info("===========================================================================================")

    if cfg.model.nemo_path:
        # '.nemo' file contains the last checkpoint and the params to initialize the model
        model.save_to(cfg.model.nemo_path)
        logging.info(f'Model is saved into `.nemo` file: {cfg.model.nemo_path}')

if __name__ == '__main__':
    main()
