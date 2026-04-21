# Copyright 2026 the Hallmark Authors
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


"""Error hierarchy for Hallmark."""


from pathlib import Path

from git.exc import GitError, GitCommandError


class HallmarkError(RuntimeError):
    """Base exception for Hallmark-specific failures."""


class DothmError(HallmarkError, GitError):
    """Raised for `.hm` repository validation and access failures."""

class CloneError(HallmarkError, GitError):
    """Raised for hallmark clone failures."""

    @staticmethod
    def _clean_message(
        message: str,
        clone_path: Path | str | None = None,
        display_path: Path | str | None = None,
    ) -> str:
        text = str(message).strip()
        if "fatal:" in text:
            text = text[text.index("fatal:"):].strip(" '")

        if clone_path is not None and display_path is not None:
            clone_path = Path(clone_path)
            display_path = Path(display_path)
            candidates = {
                str(clone_path),
                str(clone_path.resolve()),
            }
            for candidate in candidates:
                text = text.replace(candidate, str(display_path))

        return text

    @classmethod
    def from_git_command(
        cls,
        error: GitCommandError,
        fallback: str | None = None,
        clone_path: Path | str | None = None,
        display_path: Path | str | None = None,
    ) -> "CloneError":
        message = error.stderr or fallback or str(error)
        return cls(
            cls._clean_message(
                message,
                clone_path=clone_path,
                display_path=display_path,
            )
        )
