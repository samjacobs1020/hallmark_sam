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


from dataclasses import dataclass
from typing      import Optional
from pathlib     import Path

from .state      import State
from .dothm      import Dothm
from .worktree   import Worktree
from .paraframe  import ParaFrame


@dataclass(init=False)
class Repo:
    """Hallmark repository.

    This is the Python API boundary.
    It loads the in-memory ``State`` from repository ``Dothm``, and
    potentially populate the ``Worktree``.
    """

    state:    State
    dothm:    Optional[Dothm]    = None
    worktree: Optional[Worktree] = None

    @staticmethod
    def lwpaths(path: Path | str) -> tuple[Path, Path | None]:
        path = Path(path).resolve()
        if path.suffix == ".hm":
            return path, None
        return path / ".hm", path

    def __init__(self, path: Path | str) -> None:
        dothm_path, worktree_path = self.lwpaths(path)
        self.dothm    = Dothm(dothm_path)
        self.worktree = worktree_path and Worktree(worktree_path)
        self.state    = self.dothm.load()

    @classmethod
    def init(cls, path: Path | str) -> "Repo":
        dothm_path, worktree_path = cls.lwpaths(path)
        Dothm.init(dothm_path).dump(State())
        worktree_path and Worktree.init(worktree_path)
        return cls(path)

    def add(self, fstr: str) -> ParaFrame:
        if self.worktree is None:
            raise RuntimeError("cannot add files in a bare repository without a worktree")

        from contextlib import chdir
        with chdir(self.worktree):
            pf = ParaFrame(fstr)

        self.state.update(pf)
        self.dothm.dump(self.state)

        return pf

    def commit(self, msg: str, allow_empty: bool = False) -> None:
        if not isinstance(msg, str) or not msg.strip():
            raise ValueError("commit message must be a non-empty string")

        if allow_empty or self.dothm.index.diff("HEAD"):
            self.dothm.index.commit(msg)
            return True
        else:
            print("no changes added to commit")
            return False
