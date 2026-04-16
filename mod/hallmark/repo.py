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


from __future__ import annotations

import os
from contextlib  import contextmanager
from dataclasses import dataclass
from typing      import Optional
from pathlib     import Path
from hashlib     import sha1

from .state      import State
from .dothm      import Dothm
from .worktree   import Worktree
from .paraframe  import ParaFrame
from .index      import Index


@contextmanager
def chdir(path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


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
        
        common = Path(self.dothm.common_dir).resolve().parent
        self.index = Index(common)
        dothm_index = Path(dothm_path) / "index"
        main_index  = common / "index"
        if dothm_index.resolve() != main_index.resolve() and not dothm_index.exists():
            dothm_index.symlink_to(main_index)

    @classmethod
    def init(cls, path: Path | str) -> "Repo":
        dothm_path, worktree_path = cls.lwpaths(path)
        Dothm.init(dothm_path).dump(State())
        Index(dothm_path) 
        worktree_path and Worktree.init(worktree_path)
        return cls(path)

    @staticmethod
    def checksum(path: Path, chunk_size: int = 1024 * 1024) -> str:
        digest = sha1()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(chunk_size), b""):
                digest.update(block)
        return digest.hexdigest()

    def add(self, fstr: str, encoding: bool = False) -> ParaFrame:
        if self.worktree is None:
            raise RuntimeError(
                "cannot add files in a bare repository without a worktree")

        with chdir(self.worktree):
            pf = ParaFrame.parse(
                fstr,
                base_path = self.worktree,
                encodings = self.state.config.get("encodings", [])
                            if encoding else None,
                encoding = encoding,
                )

        if not pf.empty:
            pf["sha1"] = [
                self.checksum(self.worktree / path)
                for path in pf["path"].astype(str)
            ]

        self.state.update(pf)
        self.dothm.dump(self.state)
        return pf

    def commit(self, msg: str, allow_empty: bool = False) -> bool:
        if not isinstance(msg, str) or not msg.strip():
            raise ValueError("commit message must be a non-empty string")
        
        if allow_empty or self.dothm.index.diff("HEAD"):
            
            for _, row in pf.iterrows():
                self.index.store(self.worktree / row["path"], row["sha1"])
            self.dothm.index.commit(msg)
            return True
        else:
            return False

    def checkout(self, target_branch: str) -> bool:
        from shutil import copy2
        from git.exc import GitCommandError

        if not isinstance(target_branch, str) or not target_branch.strip():
            raise ValueError("branch name must be a non-empty string")

        if self.worktree is None:
            raise RuntimeError("cannot checkout a bare repository without a worktree")
        
        source = Path(self.worktree).resolve()
        target = source.parent / target_branch
        target_dothm = target / ".hm"
        
        linked_dothm = None
        
        if target_dothm.exists():
            linked_dothm = Dothm(target_dothm)
        else:
            target.mkdir(parents=True, exist_ok=True)
            existing_branches = {head.name for head in self.dothm.heads}
            try:
                if target_branch in existing_branches:
                    linked_dothm = self.dothm.link(target_dothm, target_branch)
                else:
                    self.dothm.git.worktree("add", "-b", target_branch, str(target_dothm))
                    linked_dothm = Dothm(target_dothm)
            except GitCommandError as e:
                raise RuntimeError(f'failed to create worktree for branch "{target_branch}": {e}')
            
            target_state = linked_dothm.load()
            for rel in target_state.data["path"]:
                rel_path = Path(rel)
                src = source / rel_path
                dest = target / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                copy2(src, dest)
        return True