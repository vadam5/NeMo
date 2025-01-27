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

import os
import wget
import shutil
import tempfile
import pytest

from omegaconf import OmegaConf
from nemo.collections.nlp.models import EntityLinkingModel

def get_cfg(save_dir):
    wget.download(
        "https://raw.githubusercontent.com/vadam5/NeMo/main/examples/nlp/entity_linking/conf/umls_medical_entity_linking_config.yaml",
        save_dir,
    )

    cfg_file = os.path.join(save_dir, "umls_medical_entity_linking_config.yaml")
    cfg = OmegaConf.load(cfg_file)
    cfg.model.train_ds = None
    cfg.model.validation_ds = None
    cfg.model.test_ds = None

    return cfg


class TestEntityLinkingModel:
    @pytest.mark.unit
    def test_creation_saving_restoring(self):
        # Create a new temporary directory
        with tempfile.TemporaryDirectory() as restore_dir:
            with tempfile.TemporaryDirectory() as save_dir:
                model = EntityLinkingModel(cfg=get_cfg(save_dir).model)
                assert isinstance(model, EntityLinkingModel)

                save_dir_path = save_dir

                # Where model will be saved
                model_save_path = os.path.join(save_dir, f"{model.__class__.__name__}.nemo")
                model.save_to(save_path=model_save_path)

                # Where model will be restored from
                model_restore_path = os.path.join(restore_dir, f"{model.__class__.__name__}.nemo")
                shutil.copy(model_save_path, model_restore_path)

            # at this point save_dir should not exist
            assert save_dir_path is not None and not os.path.exists(save_dir_path)
            assert not os.path.exists(model_save_path)
            assert os.path.exists(model_restore_path)

            # attempt to restore
            model_copy = model.__class__.restore_from(restore_path=model_restore_path)
            assert model.num_weights == model_copy.num_weights



if __name__ == "__main__":
    t = TestEntityLinkingModel()
    t.test_creation_saving_restoring()
