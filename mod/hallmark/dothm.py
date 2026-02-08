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


from pathlib   import Path
from functools import cached_property

from git import Repo
import pandas as pd
import yaml

from .state import State
from .error import DothmError


class Dothm(Repo):
    """Local ``.hm`` storage backend.

    The backend version controls the hallmark ``State`` database files
    (``config.yml``, ``meta.yml``, ``data.tsv``) on-disk.
    It is itself a git worktree.
    """

    @cached_property
    def path(self) -> Path:
        return Path(self.working_tree_dir)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.working_tree_dir is None:
            raise DothmError('The ".hm" directory must be a valid git worktree.')

    @classmethod
    def init(cls, *args, **kwargs) -> "Dothm":
        if kwargs.get('bare', False):
            raise DothmError('A ".hm" directory must not be a bare git repository')

        dothm = super().init(*args, **kwargs)
        readme_path = dothm.path / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("""# Local `.hm` Repository

This is a dot-hallmark repository.
It is a git-version-controlled dataset index used by `hallmark`.
See https://l6a.github.io/hallmark/ for `hallmark` usage.
""")
        dothm.index.add([readme_path])
        dothm.index.commit("Initial commit: local `.hm` repository")
        return dothm

    def load(self) -> State:
        return State(
            self.load_yml("config"),
            self.load_yml("meta"),
            self.load_tsv("data"),
        )

    def dump(self, state: State) -> None:
        self.dump_yml(state.config, "config")
        self.dump_yml(state.meta,   "meta")
        self.dump_tsv(state.data,   "data")
        self.index.add(["config.yml", "meta.yml", "data.tsv"])

    def load_yml(self, stem: Path | str) -> dict:
        with open((self.path/stem).with_suffix(".yml"), "r") as f:
            return yaml.safe_load(f)

    def dump_yml(self, data: dict, stem: Path | str) -> None:
        with open((self.path/stem).with_suffix(".yml"), "w") as f:
            yaml.dump(data, f)

    def load_tsv(self, stem: Path | str) -> pd.DataFrame:
        return pd.read_csv((self.path/stem).with_suffix(".tsv"), sep="\t")

    def dump_tsv(self, data: pd.DataFrame, stem: Path | str) -> None:
        data.to_csv((self.path/stem).with_suffix(".tsv"), sep="\t", index=False)
