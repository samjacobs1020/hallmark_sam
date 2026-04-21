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


import os
from pathlib        import Path
from contextlib     import contextmanager
from click.testing  import CliRunner

from hallmark.cli import hallmark


@contextmanager
def chdir(path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


files = [f"a{a}_i{i}.h5"
         for a in [0, 0.75, 0.975]
         for i in [0, 30, 60, 90]]

def parse(result):
    output = result.output.split('\n')[1:-1]
    return len(output), [f.strip(' ') for f in output]

def test_cli():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(hallmark, ["init", "repo"])
        assert result.exit_code == 0

        with chdir("repo"):
            assert Path(".hm").is_dir()

            for file in files:
                Path(file).write_text("test\n", encoding="utf-8")

            result = runner.invoke(hallmark, ["add", "a{a}_i{i}.h5"])
            assert result.exit_code == 0

            c, ls = parse(result)
            assert c == 12
            assert sorted(ls) == sorted(files)

            result = runner.invoke(hallmark, ["commit", "-m", "Commit test"])
            assert result.exit_code == 0
            assert "Committed staged state changes." in result.output


def test_clone_existing_destination_reports_plain_git_stderr():
    runner = CliRunner()
    with runner.isolated_filesystem():
        source = Path("source")
        result = runner.invoke(hallmark, ["init", str(source)])
        assert result.exit_code == 0

        target = Path("repo3")
        existing_hm = target / ".hm"
        existing_hm.mkdir(parents=True)
        (existing_hm / "placeholder.txt").write_text("test\n", encoding="utf-8")

        result = runner.invoke(
            hallmark,
            ["clone", "--no-fetch-data", str(source / ".hm"), str(target)],
        )

        assert result.exit_code != 0
        assert not result.output.startswith("Error:")
        assert "stderr:" not in result.output
        assert "Clone failed:" not in result.output
        assert (
            result.output.strip()
            == "fatal: destination path 'repo3' already exists and is not an empty directory."
        )
