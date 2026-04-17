# mod/hallmark/downloader.py

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

"""Remote data file downloader for hallmark repositories."""

import os
import sys
import threading
from pathlib import Path
from typing import Optional, Callable, Tuple
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .error import HallmarkError


@dataclass
class DownloadProgress:

    """Track download progress for a single file."""
    filename: str
    total_bytes: int
    downloaded_bytes: int = 0
    
    @property
    def percent(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (self.downloaded_bytes / self.total_bytes) * 100


class DownloadError(HallmarkError):
    """Raised when remote data download fails."""


class CyVerseDownloader:
    """Efficient downloader for CyVerse and HTTP-based remote sources.
    
    Handles:
    - Concurrent downloads with connection pooling
    - Streaming downloads with minimal memory footprint
    - Progress tracking and reporting
    - Resume capability for interrupted downloads
    - Automatic retry on transient failures
    """
    
    # Configuration constants
    DEFAULT_CHUNK_SIZE = 8192  # 8KB chunks for memory efficiency
    DEFAULT_MAX_WORKERS = 4    # Concurrent downloads
    CONNECT_TIMEOUT = 10
    READ_TIMEOUT = 30
    MAX_RETRIES = 3
    
    def __init__(
        self,
        max_workers: int = DEFAULT_MAX_WORKERS,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    ):
        """Initialize downloader.
        
        Args:
            max_workers: Number of concurrent download threads
            chunk_size: Size of chunks to download at once
            progress_callback: Optional callback for progress updates
        """
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.progress_callback = progress_callback
        self.session = self._create_session()
        self._lock = threading.Lock()  # For thread-safe progress updates
        
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy and connection pooling."""
        session = requests.Session()
        
        # Retry strategy for transient failures
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=1,  # Exponential backoff: 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.max_workers,
            pool_maxsize=self.max_workers,
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.mount("dav://", adapter)  # WebDAV support for CyVerse
        
        return session
    
    def _get_remote_size(self, url: str) -> int:
        """Get file size from remote server without downloading.
        
        Args:
            url: Remote file URL
            
        Returns:
            File size in bytes, or -1 if unknown
            
        Raises:
            DownloadError: If HEAD request fails
        """
        try:
            resp = self.session.head(
                url,
                timeout=(self.CONNECT_TIMEOUT, self.READ_TIMEOUT),
                allow_redirects=True
            )
            resp.raise_for_status()
            return int(resp.headers.get("content-length", -1))
        except requests.RequestException as e:
            raise DownloadError(f"Failed to get size of {url}: {e}")
    
    def _verify_file_integrity(
        self,
        filepath: Path,
        expected_sha1: Optional[str] = None
    ) -> bool:
        """Verify downloaded file integrity via checksum.
        
        Args:
            filepath: Path to downloaded file
            expected_sha1: Expected SHA1 hash, if available
            
        Returns:
            True if verified or no checksum provided, False otherwise
        """
        if not expected_sha1:
            return True
        
        try:
            sha1 = hashlib.sha1()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(self.chunk_size), b""):
                    sha1.update(chunk)
            return sha1.hexdigest() == expected_sha1
        except (IOError, OSError) as e:
            raise DownloadError(f"Failed to verify {filepath}: {e}")
    
    def _download_single_file(
        self,
        url: str,
        destination: Path,
        expected_sha1: Optional[str] = None,
    ) -> Tuple[Path, int]:
        """Download a single file with streaming and progress tracking.
        
        Args:
            url: Remote file URL
            destination: Local destination path
            expected_sha1: Expected SHA1 for verification
            
        Returns:
            Tuple of (destination_path, bytes_downloaded)
            
        Raises:
            DownloadError: If download fails
        """
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        # Check for partial download and get remote size
        try:
            remote_size = self._get_remote_size(url)
        except DownloadError as e:
            raise DownloadError(f"Cannot download {url}: {e}")
        
        # Support resume for partial downloads
        resume_header = {}
        local_size = destination.stat().st_size if destination.exists() else 0
        
        if destination.exists() and local_size < remote_size:
            resume_header = {"Range": f"bytes={local_size}-"}
        elif destination.exists() and local_size == remote_size:
            # File already fully downloaded
            return destination, local_size
        else:
            # Start fresh if file is corrupted
            destination.unlink(missing_ok=True)
        
        # Download with streaming
        progress = DownloadProgress(
            filename=destination.name,
            total_bytes=remote_size if remote_size > 0 else 0,
            downloaded_bytes=local_size if resume_header else 0
        )
        
        try:
            resp = self.session.get(
                url,
                stream=True,
                timeout=(self.CONNECT_TIMEOUT, self.READ_TIMEOUT),
                headers=resume_header,
            )
            resp.raise_for_status()
            
            mode = "ab" if resume_header else "wb"
            bytes_downloaded = local_size if resume_header else 0
            
            with open(destination, mode) as f:
                for chunk in resp.iter_content(chunk_size=self.chunk_size):
                    if chunk:  # Filter keep-alive chunks
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        progress.downloaded_bytes = bytes_downloaded
                        
                        # Thread-safe progress callback
                        if self.progress_callback:
                            with self._lock:
                                self.progress_callback(progress)
            
            # Verify integrity
            if not self._verify_file_integrity(destination, expected_sha1):
                raise DownloadError(
                    f"Checksum mismatch for {destination.name}"
                )
            
            return destination, bytes_downloaded
            
        except requests.RequestException as e:
            raise DownloadError(f"Failed to download {url}: {e}")
    
    def download_batch(
        self,
        files: list[Tuple[str, Path, Optional[str]]],
    ) -> dict:
        """Download multiple files concurrently.
        
        Args:
            files: List of (url, destination, sha1) tuples
            
        Returns:
            Dictionary with download statistics:
            {
                'succeeded': int,
                'failed': int,
                'total_bytes': int,
                'errors': list of error messages
            }
        """
        results = {
            'succeeded': 0,
            'failed': 0,
            'total_bytes': 0,
            'errors': []
        }
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all download tasks
            future_to_file = {
                executor.submit(
                    self._download_single_file,
                    url,
                    dest,
                    sha1
                ): dest
                for url, dest, sha1 in files
            }
            
            # Process completed downloads
            for future in as_completed(future_to_file):
                dest = future_to_file[future]
                try:
                    _, bytes_downloaded = future.result()
                    results['succeeded'] += 1
                    results['total_bytes'] += bytes_downloaded
                except DownloadError as e:
                    results['failed'] += 1
                    results['errors'].append(str(e))
        
        return results
    
    def close(self):
        """Close the session and clean up resources."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, *args):
        """Context manager exit."""
        self.close()


def download_remote_data(
    repo,
    worktree_path: Path,
    progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    max_workers: int = CyVerseDownloader.DEFAULT_MAX_WORKERS,
) -> dict:
    """Download remote data files for a cloned repository.
    
    Args:
        repo: Hallmark Repo instance
        worktree_path: Path to worktree where files should be downloaded
        progress_callback: Optional callback for progress updates
        max_workers: Number of concurrent downloads
        
    Returns:
        Dictionary with download statistics
        
    Raises:
        DownloadError: If remote configuration is invalid
    """
    remote_config = repo.state.config.get("remote", {})
    if not remote_config:
        return {'succeeded': 0, 'failed': 0, 'total_bytes': 0, 'errors': []}
    
    remote_url = remote_config.get("url", "").rstrip("/")
    if not remote_url:
        raise DownloadError("Remote URL not configured in config.yml")
    
    # Get list of files to download from data.tsv
    files_to_download = []
    data_df = repo.state.data
    
    if data_df.empty:
        return {'succeeded': 0, 'failed': 0, 'total_bytes': 0, 'errors': []}
    
    for _, row in data_df.iterrows():
        rel_path = Path(row['path'])
        destination = worktree_path / rel_path
        
        # Construct remote URL
        file_url = urljoin(remote_url + "/", str(rel_path))
        
        # Get SHA1 if available for verification
        sha1 = None
        if 'sha1' in row.index and pd.notna(row['sha1']):  # CORRECTED
            sha1 = row['sha1']
        
        files_to_download.append((file_url, destination, sha1))
    
    if not files_to_download:
        return {'succeeded': 0, 'failed': 0, 'total_bytes': 0, 'errors': []}
    
    # Perform concurrent downloads
    with CyVerseDownloader(
        max_workers=max_workers,
        progress_callback=progress_callback
    ) as downloader:
        return downloader.download_batch(files_to_download)