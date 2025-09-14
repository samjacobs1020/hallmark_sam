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


from pathlib import Path

from git import Repo


class Dothm(Repo):
    """Local ``.hm`` storage backend.

    The backend version controls the hallmark ``State`` database files
    (``config.yml``, ``meta.yml``, ``data.tsv``) on-disk.
    It is itself a git worktree.
    """

    @property
    def path(self) -> Path:
        if self.working_tree_dir is None:
            raise RuntimeError("local `.hm` directory has no `git` working tree")
        return Path(self.working_tree_dir)

    @classmethod
    def init(cls, *args, **kwargs) -> "Dothm":
        dothm = super().init(*args, **kwargs)
        with open(dothm.path / "README.md", "w", encoding="utf-8") as f:
            f.write("""# Local `.hm` Repository

This is a dot-hallmark repository.
It is a git-version-controlled dataset index used by `hallmark`.
See https://l6a.github.io/hallmark/ for `hallmark` usage.
""")
        dothm.index.add([readme_path])
        dothm.index.commit("Initial commit: local `.hm` repository")
        return dothm
