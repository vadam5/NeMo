# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
# Copyright 2015 and onwards Google, Inc.
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

import pynini
from denormalization.graph_utils import NEMO_CHAR, GraphFst, delete_space
from pynini.lib import pynutil


class WordFst(GraphFst):
    """
    Finite state transducer for verbalizing word
        e.g. tokens { name: "sleep" } -> sleep
    """

    def __init__(self):
        super().__init__(name="word", kind="verbalize")
        chars = pynini.closure(NEMO_CHAR - " ", 1)
        char = pynutil.delete("name:") + delete_space + pynutil.delete("\"") + chars + pynutil.delete("\"")
        self.fst = char