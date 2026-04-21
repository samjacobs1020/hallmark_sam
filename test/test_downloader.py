from pathlib import Path

import pandas as pd
import pytest

from hallmark.downloader import DownloadError, _resolve_remote_path


def test_resolve_remote_path_uses_explicit_path():
    row = pd.Series({"path": "nested/file.txt", "sha1": "abc"})

    assert _resolve_remote_path(row, []) == Path("nested/file.txt")


def test_resolve_remote_path_builds_path_from_data_format():
    row = pd.Series(
        {
            "sha1": "abc",
            "release": "SR1",
            "source": "M87",
            "year": 2017,
            "doy": 95,
            "band": "hi",
            "pipeline": "hops",
            "step": "netcal",
            "type": "StokesI",
        }
    )
    data_config = [
        {
            "fmt": (
                "{release}_{source}_{year}_{doy:03d}_{band}_"
                "{pipeline}_{step}_{type}.uvfits"
            )
        }
    ]

    assert _resolve_remote_path(row, data_config) == Path(
        "SR1_M87_2017_095_hi_hops_netcal_StokesI.uvfits"
    )


def test_resolve_remote_path_raises_when_no_path_can_be_built():
    row = pd.Series({"sha1": "abc", "release": "SR1"})

    with pytest.raises(DownloadError, match="Unable to resolve download path"):
        _resolve_remote_path(row, [{"fmt": "{missing}.uvfits"}])
