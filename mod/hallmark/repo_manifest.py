from __future__ import annotations

from pathlib import Path

import pandas as pd

from .repo_config import fmt_fields, row_to_path


def _safe_str(val) -> str | None:
    """
    Convert a value to string, handling None and NaN values.

    Args:
        val: The value to convert.

    Returns:
        The string representation of the value, or None if the value is None or NaN.
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, float) and val == int(val):
        return str(int(val))
    return str(val)


def manifest_frame_from_pf(pf, fmt: str) -> pd.DataFrame:
    """
    Convert a paraframe of paths to a manifest frame with parsed fields.
    
    Args:
        pf: A paraframe containing file paths and their corresponding SHA1 checksums.
        fmt: A format string used to parse the file paths.
    """
    if pf.empty:
        return pd.DataFrame(columns=["sha1", *fmt_fields(fmt)])

    all_fields = fmt_fields(fmt)
    pf_cols = set(pf.columns)
    rows = []
    for _, row in pf.iterrows():
        row_dict = {"sha1": row["sha1"]}
        for field in all_fields:
            # store None for missing fields or fields not present in the paraframe
            row_dict[field] = _safe_str(row[field]) if field in pf_cols else None
        rows.append(row_dict)
    return pd.DataFrame(rows, columns=["sha1", *all_fields])


def manifest_map(state) -> dict[str, str]:
    if state.data.empty:
        return {}
    data = state.config.get("data")
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        return {}
    fmt = data[0].get("fmt")
    if not isinstance(fmt, str) or not fmt.strip():
        return {}
    return {
        str(row_to_path(row, fmt)): str(row["sha1"])
        for _, row in state.data.iterrows()
    }


def frame_from_paths(repo, rel_paths: list[Path]):
    records = [{"path": str(path)} for path in rel_paths]
    pf = repo.paraframe_cls(records, base_path=repo.worktree)
    if not pf.empty:
        pf["sha1"] = [repo.checksum(repo.worktree / path) for path in rel_paths]
    return pf
