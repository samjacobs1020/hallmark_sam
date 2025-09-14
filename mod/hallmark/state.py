# Copyright 2025 the Hallmark Authors
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


from dataclasses import dataclass, field

import pandas as pd


@dataclass
class State:
    """In-memory hallmark state database.

    Attributes:
        config: Repository configuration values.
        meta:   Metadata.
        data:   Tabular file index; each row is keyed by path/change and
                stores the indexed object checksum (``sha1``).
    """

    config: dict         = field(default_factory=dict)
    meta:   dict         = field(default_factory=dict)
    data:   pd.DataFrame = field(
        default_factory=lambda: pd.DataFrame(columns=["sha1", "path"])
    )
