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


"""Hallmark CLI entrypoint and command wiring."""


import click
import sys

from click   import ClickException
from git.exc import GitError
from .error import DothmError
from .downloader import DownloadProgress

from . import Repo  # from "__init__.py"


@click.group()
@click.version_option()
@click.pass_context
def hallmark(ctx):
    """Reproducibility is the hallmark of the scientific method.

    Hallmark is a lightweight package designed to version control and
    manage data products in a complex workflow.
    """
    if ctx.invoked_subcommand in [None, "init", "clone"]:
        return  # do nothing

    try:
        ctx.obj = Repo(".")
    except GitError as e:
        raise ClickException(
            f"Failed to open hallmark repository: {e}")


@hallmark.command(short_help="Initialize a hallmark repository.")
@click.argument("path")
def init(path):
    """Initialize a hallmark repository at PATH.

    If PATH ends with `.hm`, a bare repository is created.
    Otherwise, a `.hm` directory is created inside PATH.
    """
    try:
        Repo.init(path)
    except GitError as e:
        raise ClickException(
            f'Failed to initialize hallmark repository at "{path}": {e}')


@hallmark.command(short_help="Show information of the current directory.")
@click.pass_obj
def info(repo):
    """Show hallmark repository information of the current directory.

    Display local `.hm` and worktree locations for the current
    directory.
    """
    click.echo(f'dot-hallmark repo: "{repo.dothm.path}"')
    click.echo(f'hallmark worktree: "{repo.worktree}"')


@hallmark.command(short_help="Add files to hallmark index using a Python f-string.")
@click.argument("fstring")
@click.pass_obj
def add(repo, fstring):
    """Add files discovered via a Python format string to the hallmark index.

    This is analogous to `git add FILE`, which adds file contents to
    the "index" (also known as the "staging area").
    Instead of specifying file names directly, this function uses a
    Python format string (i.e., an f-string) to discover and add
    matching files to the hallmark index.
    """
    pf = repo.add(fstring)

    if pf.empty:
        click.echo("No files matched the format string.")
    else:
        click.echo("Changes to be committed")
        click.echo(pf.path.to_string(index=False, header=False))


@hallmark.command(short_help="Commit changes to the repository.")
@click.option("-m", "message", required=True)
@click.pass_obj
def commit(repo, message):
    """Commit changes in the index to the hallmark repository.

    This is analogous to `git commit -m MESSAGE`.
    """
    if repo.commit(message):
        click.echo("Committed staged state changes.")
    else:
        click.echo("No changes added to commit.")

@hallmark.command(short_help="Checkout to a worktree branch.")
@click.argument("target_branch")
@click.pass_obj
def checkout(repo, target_branch):
    """Checkout to another worktree branch and restore the state saved in data.tsv.

    This is analogous to `git checkout BRANCH`.
    """
    if repo.checkout(target_branch):
        click.echo(f'Checked out to "{target_branch}".')
    else:
        click.echo("No branches to checkout.")

# Updated mod/hallmark/cli.py section

@hallmark.command(short_help="Clone a hallmark repository from a remote URL.")
@click.argument("url")
@click.argument("path")
@click.option(
    "--no-fetch-data",
    is_flag=True,
    help="Skip downloading remote data files after clone.")
@click.option(
    "--max-workers",
    type=int,
    default=4,
    show_default=True,
    help="Number of concurrent downloads.")
def clone(url, path, no_fetch_data, max_workers):
    """Clone a hallmark repository from URL to PATH.
    
    By default, also downloads data files from the configured remote URL.
    Use --no-fetch-data to skip this step.
    
    Supports concurrent downloads for efficient retrieval of large datasets.
    """
    try:
        repo = Repo.clone(url, path)
        click.echo(f'Successfully cloned to "{path}"')
        
        if not no_fetch_data:
            dothm_path, worktree_path = Repo.lwpaths(path)
            if worktree_path is None:
                click.echo("Bare repository clone; skipping data download.")
                return
            
            # Setup progress callback for CLI
            def progress_callback(progress: DownloadProgress):
                """Display download progress."""
                percent = progress.percent
                bar_length = 40
                filled = int(bar_length * percent / 100)
                bar = "█" * filled + "░" * (bar_length - filled)
                mb_downloaded = progress.downloaded_bytes / (1024 * 1024)
                mb_total = progress.total_bytes / (1024 * 1024)
                sys.stdout.write(
                    f"\r{progress.filename}: [{bar}] "
                    f"{percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)"
                )
                sys.stdout.flush()
            
            click.echo("Downloading remote data files...")
            from .downloader import download_remote_data, DownloadError
            
            results = download_remote_data(
                repo,
                worktree_path,
                progress_callback=progress_callback,
                max_workers=max_workers,
            )
            
            click.echo()  # New line after progress bar
            
            if results['failed'] == 0:
                mb_total = results['total_bytes'] / (1024 * 1024)
                click.echo(
                    f"✓ Successfully downloaded {results['succeeded']} files "
                    f"({mb_total:.1f} MB)"
                )
            else:
                click.echo(
                    f"⚠ Download completed with errors: "
                    f"{results['succeeded']} succeeded, "
                    f"{results['failed']} failed"
                )
                for error in results['errors']:
                    click.echo(f"  - {error}", err=True)
                
                if results['failed'] == len(results['errors']):
                    raise ClickException(
                        f"Failed to download {results['failed']} file(s)"
                    )
    
    except (DothmError, GitError) as e:
        raise ClickException(f'Clone failed: {e}')