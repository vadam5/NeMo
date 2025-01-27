# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
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

import pytest
import torch

from nemo.collections.asr.parts import jasper


class TestJasperBlock:
    def jasper_base_config(self, **kwargs):
        base = dict(
            inplanes=16,
            planes=8,
            kernel_size=[11],
            repeat=1,
            stride=[1],
            dilation=[1],
            activation="relu",
            conv_mask=True,
            separable=False,
            se=False,
        )
        base.update(kwargs)
        return base

    def check_module_exists(self, module, cls):
        global _MODULE_EXISTS
        _MODULE_EXISTS = 0

        def _traverse(m):
            if isinstance(m, cls):
                global _MODULE_EXISTS
                _MODULE_EXISTS += 1

        module.apply(_traverse)
        assert _MODULE_EXISTS > 0

    @pytest.mark.unit
    def test_basic_block(self):
        config = self.jasper_base_config(residual=False)
        act = jasper.jasper_activations.get(config.pop('activation'))()

        block = jasper.JasperBlock(**config, activation=act)

        x = torch.randn(1, 16, 131)
        xlen = torch.tensor([131])
        y, ylen = block(([x], xlen))

        assert isinstance(block, jasper.JasperBlock)
        assert y[0].shape == torch.Size([1, config['planes'], 131])
        assert ylen[0] == 131

    @pytest.mark.unit
    def test_residual_block(self):
        config = self.jasper_base_config(residual=True)
        act = jasper.jasper_activations.get(config.pop('activation'))()

        block = jasper.JasperBlock(**config, activation=act)

        x = torch.randn(1, 16, 131)
        xlen = torch.tensor([131])
        y, ylen = block(([x], xlen))

        assert isinstance(block, jasper.JasperBlock)
        assert y[0].shape == torch.Size([1, config['planes'], 131])
        assert ylen[0] == 131

    @pytest.mark.unit
    def test_basic_block_repeat(self):
        config = self.jasper_base_config(residual=False, repeat=3)
        act = jasper.jasper_activations.get(config.pop('activation'))()

        block = jasper.JasperBlock(**config, activation=act)

        x = torch.randn(1, 16, 131)
        xlen = torch.tensor([131])
        y, ylen = block(([x], xlen))

        assert isinstance(block, jasper.JasperBlock)
        assert y[0].shape == torch.Size([1, config['planes'], 131])
        assert ylen[0] == 131
        assert len(block.mconv) == 3 * 3 + 1  # (3 repeats x {1 conv + 1 norm + 1 dropout} + final conv)

    @pytest.mark.unit
    def test_basic_block_repeat_stride(self):
        config = self.jasper_base_config(residual=False, repeat=3, stride=[2])
        act = jasper.jasper_activations.get(config.pop('activation'))()

        block = jasper.JasperBlock(**config, activation=act)

        x = torch.randn(1, 16, 131)
        xlen = torch.tensor([131])
        y, ylen = block(([x], xlen))

        assert isinstance(block, jasper.JasperBlock)
        assert y[0].shape == torch.Size([1, config['planes'], 17])  # 131 // (stride ^ repeats)
        assert ylen[0] == 17  # 131 // (stride ^ repeats)
        assert len(block.mconv) == 3 * 3 + 1  # (3 repeats x {1 conv + 1 norm + 1 dropout} + final conv)

    @pytest.mark.unit
    def test_basic_block_repeat_stride_last(self):
        config = self.jasper_base_config(residual=False, repeat=3, stride=[2], stride_last=True)
        act = jasper.jasper_activations.get(config.pop('activation'))()

        block = jasper.JasperBlock(**config, activation=act)

        x = torch.randn(1, 16, 131)
        xlen = torch.tensor([131])
        y, ylen = block(([x], xlen))

        assert isinstance(block, jasper.JasperBlock)
        assert y[0].shape == torch.Size([1, config['planes'], 66])  # 131 // stride
        assert ylen[0] == 66  # 131 // stride
        assert len(block.mconv) == 3 * 3 + 1  # (3 repeats x {1 conv + 1 norm + 1 dropout} + final conv)

    @pytest.mark.unit
    def test_basic_block_repeat_separable(self):
        config = self.jasper_base_config(residual=False, repeat=3, separable=True)
        act = jasper.jasper_activations.get(config.pop('activation'))()

        block = jasper.JasperBlock(**config, activation=act)

        x = torch.randn(1, 16, 131)
        xlen = torch.tensor([131])
        y, ylen = block(([x], xlen))

        assert isinstance(block, jasper.JasperBlock)
        assert y[0].shape == torch.Size([1, config['planes'], 131])
        assert ylen[0] == 131
        assert len(block.mconv) == 3 * 4 + 1  # (3 repeats x {1 dconv + 1 pconv + 1 norm + 1 dropout} + final conv)

    @pytest.mark.unit
    def test_basic_block_stride(self):
        config = self.jasper_base_config(stride=[2], residual=False)
        act = jasper.jasper_activations.get(config.pop('activation'))()

        print(config)
        block = jasper.JasperBlock(**config, activation=act)

        x = torch.randn(1, 16, 131)
        xlen = torch.tensor([131])
        y, ylen = block(([x], xlen))

        assert isinstance(block, jasper.JasperBlock)
        assert y[0].shape == torch.Size([1, config['planes'], 66])
        assert ylen[0] == 66

    @pytest.mark.unit
    def test_residual_block_stride(self):
        config = self.jasper_base_config(stride=[2], residual=True, residual_mode='stride_add')
        act = jasper.jasper_activations.get(config.pop('activation'))()

        print(config)
        block = jasper.JasperBlock(**config, activation=act)

        x = torch.randn(1, 16, 131)
        xlen = torch.tensor([131])
        y, ylen = block(([x], xlen))

        assert isinstance(block, jasper.JasperBlock)
        assert y[0].shape == torch.Size([1, config['planes'], 66])
        assert ylen[0] == 66

    @pytest.mark.unit
    def test_residual_block_activations(self):
        for activation in jasper.jasper_activations.keys():
            config = self.jasper_base_config(activation=activation)
            act = jasper.jasper_activations.get(config.pop('activation'))()

            block = jasper.JasperBlock(**config, activation=act)

            x = torch.randn(1, 16, 131)
            xlen = torch.tensor([131])
            y, ylen = block(([x], xlen))

            self.check_module_exists(block, act.__class__)
            assert isinstance(block, jasper.JasperBlock)
            assert y[0].shape == torch.Size([1, config['planes'], 131])
            assert ylen[0] == 131

    @pytest.mark.unit
    def test_residual_block_normalizations(self):
        NORMALIZATIONS = ["batch", "layer", "group"]
        for normalization in NORMALIZATIONS:
            config = self.jasper_base_config(normalization=normalization)
            act = jasper.jasper_activations.get(config.pop('activation'))()

            block = jasper.JasperBlock(**config, activation=act)

            x = torch.randn(1, 16, 131)
            xlen = torch.tensor([131])
            y, ylen = block(([x], xlen))

            assert isinstance(block, jasper.JasperBlock)
            assert y[0].shape == torch.Size([1, config['planes'], 131])
            assert ylen[0] == 131

    @pytest.mark.unit
    def test_residual_block_se(self):
        config = self.jasper_base_config(se=True, se_reduction_ratio=8)
        act = jasper.jasper_activations.get(config.pop('activation'))()

        block = jasper.JasperBlock(**config, activation=act)

        x = torch.randn(1, 16, 131)
        xlen = torch.tensor([131])
        y, ylen = block(([x], xlen))

        self.check_module_exists(block, jasper.SqueezeExcite)
        assert isinstance(block, jasper.JasperBlock)
        assert y[0].shape == torch.Size([1, config['planes'], 131])
        assert ylen[0] == 131

    @pytest.mark.unit
    def test_residual_block_asymmetric_pad_future_contexts(self):
        # test future contexts at various values
        # 0 = no future context
        # 2 = limited future context
        # 5 = symmetric context
        # 8 = excess future context (more future context than present or past context)
        future_contexts = [0, 2, 5, 8]
        for future_context in future_contexts:
            print(future_context)
            config = self.jasper_base_config(future_context=future_context)
            act = jasper.jasper_activations.get(config.pop('activation'))()

            block = jasper.JasperBlock(**config, activation=act)

            x = torch.randn(1, 16, 131)
            xlen = torch.tensor([131])
            y, ylen = block(([x], xlen))

            self.check_module_exists(block, torch.nn.ConstantPad1d)
            self.check_module_exists(block, jasper.MaskedConv1d)

            assert isinstance(block, jasper.JasperBlock)
            assert y[0].shape == torch.Size([1, config['planes'], 131])
            assert ylen[0] == 131
            assert block.mconv[0].pad_layer is not None
            assert block.mconv[0]._padding == (config['kernel_size'][0] - 1 - future_context, future_context)

    @pytest.mark.unit
    def test_residual_block_asymmetric_pad_future_context_fallback(self):
        # test future contexts at various values
        # 15 = K < FC; fall back to symmetric context
        future_context = 15
        print(future_context)
        config = self.jasper_base_config(future_context=future_context)
        act = jasper.jasper_activations.get(config.pop('activation'))()

        block = jasper.JasperBlock(**config, activation=act)

        x = torch.randn(1, 16, 131)
        xlen = torch.tensor([131])
        y, ylen = block(([x], xlen))

        self.check_module_exists(block, jasper.MaskedConv1d)

        assert isinstance(block, jasper.JasperBlock)
        assert y[0].shape == torch.Size([1, config['planes'], 131])
        assert ylen[0] == 131
        assert block.mconv[0].pad_layer is None
        assert block.mconv[0]._padding == config['kernel_size'][0] // 2
