from pathlib import Path
import shutil
import pytest
import pandas as pd
from io import StringIO
from hallmark import ParaFrame, Repo
from hallmark.eht_datatree import build_tree, detect_fmt, build_repo


sample_fmt = "SR1_M87_{year}_{day}_{band}_hops_netcal_StokesI.{ext}"
DATASET = "test_dataset"
FMT = "ER6_SGRA_2017_{scan}_{band}_{pipeline}_netcal-LMTcal-{method}_StokesI"


def _write_dataset(root: Path) -> None:
    """
    Write a minimal EHT-style dataset for testing.

    Args:
        root: Path to the root directory where the dataset will be created.

    Returns: None
    """
    (root / "README.md").write_text("readme", encoding="utf-8")
    (root / "LICENSE.txt").write_text("license", encoding="utf-8")
    for stem, exts in [
        ("ER6_SGRA_2017_097_hi_hops_netcal-LMTcal-besttime_StokesI", ["csv", "txt"]),
        ("ER6_SGRA_2017_097_lo_casa_netcal-LMTcal-norm_StokesI", ["csv", "txt"]),
        ("ER6_SGRA_2017_096_hi_hops_netcal-LMTcal_StokesI", ["csv", "txt"]),
    ]:
        for ext in exts:
            # make a subdirectory for each extension to simulate EHT-style dataset
            subdir = root / f"data_{ext}"
            subdir.mkdir(exist_ok=True)
            (subdir / f"{stem}.{ext}").write_text(stem, encoding="utf-8")


def _make_archive(directory: Path, stem: str, fmt: str = "gztar",
                   contents: dict[str, str] | None = None) -> Path:
    """Create a real archive in `directory` and return its actual path.

    Args:
        directory: Path to the directory where the archive will be created.
        stem: Stem name for the archive file (without extension).
        fmt: Format of the archive (e.g., "gztar", "zip").
        contents: Optional dictionary of file names and their contents to include
                  in the archive instead of the default dummy file.
    """
    contents_dir = directory / f"_{stem}_src"
    contents_dir.mkdir(exist_ok=True)
    if contents:
        # create archive with contents
        for name, text in contents.items():
            (contents_dir / name).write_text(text, encoding="utf-8")
    else:
        # create archive with a single dummy file
        (contents_dir / "dummy.txt").write_text("dummy", encoding="utf-8")

    archive_path = shutil.make_archive(
        str(directory / stem), fmt, root_dir=str(contents_dir))
    shutil.rmtree(contents_dir)
    return Path(archive_path)


# create test dataset fixture
@pytest.fixture
def eht_dataset(tmp_path):

    # create subdirectories
    (tmp_path / "csv").mkdir()
    (tmp_path / "txt").mkdir()
    (tmp_path / "uvfits").mkdir()

    # write meta files
    for file_name in ["README.md", "LICENSE.txt", "run.sh"]:
        (tmp_path / file_name).write_text(file_name, encoding="utf-8")

    # write script files
    for file_name in ["csv/dump_csv.py", 
                      "txt/dump_txt.py", 
                      "uvfits/convert_stokesI.py"]:
        (tmp_path / file_name).write_text(file_name, encoding="utf-8")

    # write drive files
    for stem in ["csv", "txt", "uvfits"]:
        _make_archive(tmp_path, f"EHTC_FirstM87Results_Apr2019_{stem}")

    # write data files — 2 stems, 3 formats each
    for stem in [
        "SR1_M87_2017_095_hi_hops_netcal_StokesI",
        "SR1_M87_2017_095_lo_hops_netcal_StokesI",
    ]:
        for ext in ["csv", "txt", "uvfits"]:
            (tmp_path / ext / f"{stem}.{ext}").write_text(stem, encoding="utf-8")

    return tmp_path

# create fixture for build_tree result to use in multiple tests
@pytest.fixture
def sample_tree(eht_dataset):
    return build_tree(eht_dataset, sample_fmt)


@pytest.fixture
def dataset(tmp_path):
    root = tmp_path / "dataset"
    root.mkdir()
    _write_dataset(root)
    return root


@pytest.fixture
def repo_path(tmp_path):
    return tmp_path / "hallmark_repo"


@pytest.fixture
def built_repo(dataset, repo_path):
    tree = build_tree(dataset, FMT, data_type="L2")
    return build_repo(
        tree=tree,
        repo_path=repo_path,
        dataset_name=DATASET,
        worktree_root=dataset,
    )

### build_tree structure tests ###

def test_build_tree_raises_if_root_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_tree(tmp_path / "nonexistent", sample_fmt)

# verify build_tree resolves string inputs for the root path
def test_build_tree_accepts_string_path(eht_dataset):
    tree = build_tree(str(eht_dataset), sample_fmt)
    assert isinstance(tree, dict), f"expected dict for tree, got {type(tree)}"
    assert "meta" in tree, f"expected 'meta' key in tree, got {tree.keys()}"
    assert "data" in tree, f"expected 'data' key in tree, got {tree.keys()}"

# test that each branch and stem are the right type
def test_build_tree_structure(sample_tree):
    assert isinstance(sample_tree, dict), f"expected dict for tree, \
                                            got {type(sample_tree)}"
    assert "meta" in sample_tree, f"expected 'meta' key in tree, \
                                    got {sample_tree.keys()}"
    assert "data" in sample_tree, f"expected 'data' key in tree, \
                                    got {sample_tree.keys()}"
    assert isinstance(sample_tree["meta"], ParaFrame), f"expected ParaFrame for meta, \
                                    got {type(sample_tree['meta'])}"
    assert isinstance(sample_tree["data"], dict), f"expected dict for data, \
                                    got {type(sample_tree['data'])}"

# needs unique dataset to test for ext column presence when not in fmt string
def test_build_tree_ext_column_always_present(tmp_path):
    (tmp_path / "csv").mkdir()
    (tmp_path / "csv" / "SR1_M87_2017_095_hi.csv").write_text(
        "data", encoding="utf-8")
    fmt = "SR1_M87_{year}_{day}_{band}.csv"
    tree = build_tree(tmp_path, fmt)
    for fmt_str, fmt_dict in tree["data"].items():
        for stem_key, stem_pf in fmt_dict.items():
            assert "ext" in stem_pf.columns, \
                f"ext column not present in {fmt_str}/{stem_key}"

### build_tree meta branch tests ###

# needs its own fixture to test hallmark's .hm is ignored
def test_build_tree_ignores_dot_hm_directory(built_repo, tmp_path):
    # create a file inside .hm and verify it's not picked up by meta
    hm_dir = tmp_path / ".hm"
    hm_dir.mkdir()
    (hm_dir / "config.yml").write_text("config", encoding="utf-8")
    (tmp_path / "visible.txt").write_text("visible", encoding="utf-8")
    tree = build_tree(tmp_path, "data/{name}.txt")
    meta_paths = list(tree["meta"]["path"])
    assert "visible.txt" in meta_paths, "visible.txt not in meta"
    assert not any(".hm" in p for p in meta_paths), ".hm directory leaked into meta"


# verify that the meta branch contains only the file path and is sorted 
def test_build_tree_meta_schema(sample_tree):
    columns = sorted(list(sample_tree["meta"].columns))
    assert columns == ["ext", "path"], \
        f"meta has unexpected columns: {columns}"
    branch_list = list(sample_tree["meta"]["path"])
    assert branch_list == sorted(sample_tree["meta"]["path"]), \
        "meta branch is not sorted alphabetically"
            
### extraction tests ###

def test_build_tree_extracts_archives_in_L1_mode(tmp_path):
    project_dir = tmp_path / "2016.1.01114.V"
    project_dir.mkdir()
    _make_archive(project_dir, "extract1", contents={"a.csv": "data"})
    tree = build_tree(tmp_path, "{name}.csv", data_type="L1")
    project = tree["2016.1.01114.V"]
    drive_keys = [k for k in project if k not in ("meta",)]
    assert len(drive_keys) == 1, \
        f"expected one extracted drive folder, got {drive_keys}"


def test_build_tree_archives_not_in_data_branch(tmp_path):
    _make_archive(tmp_path, "data1", "gztar")
    _make_archive(tmp_path, "data2", "zip")
    tree = build_tree(tmp_path, "{name}")
    if "data" in tree:
        for fmt_dict in tree["data"].values():
            for stem_pf in fmt_dict.values():
                for path in stem_pf["path"]:
                    ext = Path(path).suffix.lower()
                    assert ext not in {".tgz", ".tar", ".gz", ".zip", ".bz2",
                                       ".xz", ".zst", ".7z", ".rar"}, \
                        f"archive file '{path}' leaked into data branch"


def test_build_tree_no_archives_produces_no_drive_key(tmp_path):
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    tree = build_tree(tmp_path, "{name}")
    assert "drives" not in tree, "drives key should not appear in tree"

#### build_tree data branch tests ###

# verify that every file is assigned to only one branch and are accounted for
def test_build_tree_partitioning_and_completeness(eht_dataset, sample_tree):
    meta_paths = set(sample_tree["meta"]["path"])
    data_paths = {
        path
        for fmt_dict in sample_tree["data"].values()
        for stem_pf in fmt_dict.values()
        for path in stem_pf["path"]}
    assert meta_paths.isdisjoint(data_paths), \
        f"meta and data have common files: {sorted(meta_paths & data_paths)}"

    all_tracked = meta_paths | data_paths
    expected = {
        str(p.relative_to(eht_dataset))
        for p in eht_dataset.rglob("*")
        if p.is_file()}
    assert all_tracked.issubset(expected), \
        f"Tracked files not on disk: {all_tracked - expected}"


def test_build_tree_data_empty_when_no_fmt_matches(eht_dataset):
    tree = build_tree(eht_dataset, "{ext}/NONEXISTENT_{year}_{day}.{ext}")
    assert "data" not in tree, "data key should be omitted when no fmt matches"


def test_build_tree_data_matches_mixed_delimiters(tmp_path):
    (tmp_path / "ER6_SGRA_2017_096_hi_hops_netcal-LMTcal_StokesI.csv").write_text(
        "data", encoding="utf-8")
    fmt = "ER6_SGRA_2017_{day}_{band}_{pipeline}_netcal_LMTcal_StokesI"
    tree = build_tree(tmp_path, fmt)
    assert len(tree["data"]) == 1, \
        f"expected 1 fmt despite delimiter mismatch, got {len(tree['data'])}"
    

def test_build_tree_auto_detected_fmt_matches_mixed_delimiters(tmp_path):
    (tmp_path / "ER6_SGRA_2017_096_hi_hops_netcal-LMTcal_StokesI.csv").write_text(
        "data", encoding="utf-8")
    (tmp_path / "ER6_SGRA_2017_097_lo_casa_netcal-LMTcal_StokesI.csv").write_text(
        "data", encoding="utf-8")
    # fmt is None, triggers auto-detection
    tree = build_tree(tmp_path)  
    assert len(tree["data"]) == 1, \
        f"expected 1 fmt, got {len(tree['data'])}"
    fmt_dict = list(tree["data"].values())[0]
    total_files = sum(len(pf) for pf in fmt_dict.values())
    assert total_files == 2, \
        f"expected 2 files total across stems, got {total_files}"
    

# needs unique dataset to test for single stem handling
def test_build_tree_single_stem(tmp_path):
    (tmp_path / "csv").mkdir()
    (tmp_path / "csv" / "SR1_M87_2017_095_hi_hops_netcal_StokesI.csv").write_text(
        "data", encoding="utf-8")
    tree = build_tree(tmp_path, sample_fmt)
    assert len(tree["data"]) == 1, \
        f"length should be 1 but len={len(tree['data'])}"

# test that each data stem contains the expected number of files and schema
def test_build_tree_data_content(sample_tree):
    data = sample_tree["data"]
    assert len(data) == 1, f"expected 1 fmt, got {len(data)}"
    fmt_dict = list(data.values())[0]
    stems = list(fmt_dict.keys())
    assert len(stems) == 2, f"expected 2 stems, got {len(stems)}"
    for stem in stems:
        assert len(fmt_dict[stem]) == 3, \
            f"{stem} has {len(fmt_dict[stem])} files, expected 3"
    

### fmt variations tests ###

# needs unique dataset to test for nested subdirectory handling
def test_build_tree_nested_subdir_fmt(tmp_path):
    (tmp_path / "casa_data" / "April05").mkdir(parents=True)
    (tmp_path / "hops_data" / "April05").mkdir(parents=True)
    (tmp_path / "casa_data" / "April05" / "SR2_M87_2017_095_hi_casa.uvfits").write_text(
        "data", encoding="utf-8")
    (tmp_path / "hops_data" / "April05" / "SR2_M87_2017_095_hi_hops.uvfits").write_text(
        "data", encoding="utf-8")
    fmt = "SR2_M87_{year}_{day}_{band}_{pipeline}.uvfits"
    tree = build_tree(tmp_path, fmt)
    assert len(tree["data"]) == 1
    fmt_dict = list(tree["data"].values())[0]
    stems = list(fmt_dict.keys())
    assert len(stems) == 2, \
        f"expected 2 stems but got {len(stems)}, couldn't parse nested directories"
    
### detect_fmt tests ###

def test_detect_fmt_finds_single_pattern(tmp_path):
    (tmp_path / "csv").mkdir()
    (tmp_path / "csv" / "SR1_M87_2017_095_hi_hops_netcal_StokesI.csv").write_text(
        "data", encoding="utf-8")
    (tmp_path / "csv" / "SR1_M87_2017_096_lo_hops_netcal_StokesI.csv").write_text(
        "data", encoding="utf-8")
    fmts = detect_fmt(tmp_path)
    assert fmts == ["SR1_M87_2017_{p0}_{p1}_hops_netcal_StokesI"], f"unexpected fmts: \
    {fmts}, expected 'SR1_M87_2017_{{p0}}_{{p1}}_hops_netcal_StokesI'"


def test_detect_fmt_excludes_script_extensions(tmp_path):
    (tmp_path / "csv").mkdir()
    (tmp_path / "csv" / "SR1_M87_2017_095_hi.csv").write_text(
        "data", encoding="utf-8")
    (tmp_path / "csv" / "SR1_M87_2017_096_lo.csv").write_text(
        "data", encoding="utf-8")
    (tmp_path / "csv" / "dump_csv.py").write_text(
        "data", encoding="utf-8")
    (tmp_path / "csv" / "convert.py").write_text(
        "data", encoding="utf-8")
    fmts = detect_fmt(tmp_path)
    assert all("dump" not in fmt for fmt in fmts), \
        f"dump files leaked into fmts: {fmts}"
    assert all("convert" not in fmt for fmt in fmts), \
        f"convert files leaked into fmts: {fmts}"

def test_detect_fmt_excludes_known_meta_files(tmp_path):
    (tmp_path / "README.txt").write_text("data", encoding="utf-8")
    (tmp_path / "LICENSE.txt").write_text("data", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "SR1_M87_2017_095_hi.txt").write_text(
        "data", encoding="utf-8")
    (tmp_path / "data" / "SR1_M87_2017_096_lo.txt").write_text(
        "data", encoding="utf-8")
    fmts = detect_fmt(tmp_path)
    assert all("README" not in fmt for fmt in fmts), \
        f"README file leaked into fmts: {fmts}"
    assert all("LICENSE" not in fmt for fmt in fmts), \
        f"LICENSE file leaked into fmts: {fmts}"

def test_detect_fmt_merges_when_a_shared_token_exists(tmp_path):
    (tmp_path / "csv").mkdir()
    (tmp_path / "csv" / "SR1_M87_2017_095.csv").write_text("data", encoding="utf-8")
    (tmp_path / "csv" / "SR1_M87_2017_096.csv").write_text("data", encoding="utf-8")
    (tmp_path / "csv" / "ER6_SGRA_2017_097.csv").write_text("data", encoding="utf-8")
    (tmp_path / "csv" / "ER6_SGRA_2017_098.csv").write_text("data", encoding="utf-8")
    fmts = detect_fmt(tmp_path)
    assert fmts == ["{p0}_{p1}_2017_{p2}"], \
        f"expected one merged fmt via shared '2017' token, got {fmts}"

def test_detect_fmt_merges_optional_trailing_field(tmp_path):
    (tmp_path / "csv").mkdir()
    (tmp_path / "csv" / "ER6_SGRA_2017_095_hi_netcal_StokesI.csv").write_text(
        "data", encoding="utf-8")
    (tmp_path / "csv" / "ER6_SGRA_2017_096_lo_netcal_StokesI.csv").write_text(
        "data", encoding="utf-8")
    (tmp_path / "csv" / "ER6_SGRA_2017_097_hi_netcal_norm_StokesI.csv").write_text(
        "data", encoding="utf-8")
    (tmp_path / "csv" / "ER6_SGRA_2017_098_lo_netcal_besttime_StokesI.csv").write_text(
        "data", encoding="utf-8")
    fmts = detect_fmt(tmp_path)
    assert fmts == ["ER6_SGRA_2017_{p0}_{p1}_netcal_{p2}_StokesI"], \
        f"expected one merged fmt with optional suffix, got {fmts}"


def test_detect_fmt_returns_empty_when_no_data_files(tmp_path):
    (tmp_path / "README.md").write_text("data", encoding="utf-8")
    (tmp_path / "LICENSE.txt").write_text("data", encoding="utf-8")
    (tmp_path / "run.sh").write_text("data", encoding="utf-8")
    fmts = detect_fmt(tmp_path)
    assert fmts == [], f"expected empty list, got {fmts}"


def test_detect_fmt_used_automatically_when_fmt_is_none(tmp_path):
    (tmp_path / "SR1_M87_2017_095_hi.csv").write_text(
        "data", encoding="utf-8")
    (tmp_path / "SR1_M87_2017_096_lo.csv").write_text(
        "data", encoding="utf-8")
    tree = build_tree(tmp_path)
    assert len(tree["data"]) == 1, \
        f"expected 1 fmt, got {len(tree['data'])}"


def test_build_tree_data_multiple_fmts_produce_separate_branches(tmp_path):
    (tmp_path / "SR1_M87_2017_095_hi.csv").write_text("data", encoding="utf-8")
    (tmp_path / "ER6_SGRA_2017_096_lo.csv").write_text("data", encoding="utf-8")
    fmts = [
        "SR1_M87_{year}_{day}_{band}",
        "ER6_SGRA_{year}_{day}_{band}",
    ]
    tree = build_tree(tmp_path, fmts)
    assert len(tree["data"]) == 2, \
        f"expected 2 fmt branches, got {len(tree['data'])}"


def test_detect_fmt_merges_when_shared_tokens_exist(tmp_path):
    (tmp_path / "AA_B_1_0AXG5H.dat").write_text("data", encoding="utf-8")
    (tmp_path / "AA_B_2_0AXG5H.dat").write_text("data", encoding="utf-8")
    (tmp_path / "AP_B_3_0AXG5H.dat").write_text("data", encoding="utf-8")
    (tmp_path / "AP_B_4_0AXG5H.dat").write_text("data", encoding="utf-8")
    fmts = detect_fmt(tmp_path)
    assert fmts == ["{p0}_B_{p1}_0AXG5H"], \
        f"expected one merged fmt via shared 'B'/'0AXG5H' tokens, got {fmts}"


def test_build_tree_data_ext_column_has_no_period(tmp_path):
    (tmp_path / "SR1_M87_2017_095_hi.csv").write_text("data", encoding="utf-8")
    (tmp_path / "SR1_M87_2017_096_lo.csv").write_text("data", encoding="utf-8")
    fmt = "SR1_M87_{year}_{day}_{band}.csv"
    tree = build_tree(tmp_path, fmt)
    fmt_dict = list(tree["data"].values())[0]
    for stem_pf in fmt_dict.values():
        exts = set(stem_pf["ext"])
        assert all("." not in e for e in exts), \
            f"expected ext without period, got {exts}"


### L1 / recursive build_tree tests ###

def test_build_tree_L1_recurses_into_subfolders(tmp_path):
    # a project with no drives, just a nested extract-like subfolder
    extract_dir = tmp_path / "2016.1.01114.V"
    extract_dir.mkdir()
    (extract_dir / "README.txt").write_text("readme", encoding="utf-8")
    tree = build_tree(tmp_path, None, data_type="L1")
    assert "2016.1.01114.V" in tree, "subfolder not recursed into at L1"
    assert "meta" in tree["2016.1.01114.V"], \
        "expected meta at the recursed-into subfolder level"


def test_build_tree_L1_extracts_drive_and_switches_to_L2(tmp_path):
    project_dir = tmp_path / "2016.1.01114.V"
    project_dir.mkdir()
    _make_archive(
        project_dir, "extract1",
        contents={
            "SR1_M87_2017_095_hi.csv": "data",
            "SR1_M87_2017_096_lo.csv": "data",
        },
    )
    fmt = "SR1_M87_{year}_{day}_{band}.csv"
    tree = build_tree(tmp_path, fmt, data_type="L1")
    extract_keys = [k for k in tree["2016.1.01114.V"] if k not in ("meta",)]
    assert len(extract_keys) == 1, \
        f"expected exactly one extracted drive folder, got {extract_keys}"

    extracted = tree["2016.1.01114.V"][extract_keys[0]]
    assert "data" in extracted, "extracted drive should be treated as L2 (has data)"
    assert len(extracted["data"]) == 1, "expected 1 fmt match inside extracted drive"


def test_build_tree_L1_intermediate_level_has_no_data_key(tmp_path):
    # files directly in an L1-level folder (not inside an extracted drive)
    # should fall to meta, never produce a "data" key at this level
    (tmp_path / "loose_file.csv").write_text("data", encoding="utf-8")
    tree = build_tree(tmp_path, "{name}.csv", data_type="L1")
    assert "data" not in tree, \
        "L1 intermediate level should never build a data branch directly"
    assert "loose_file.csv" in list(tree["meta"]["path"]), \
        "loose file at L1 level should land in meta"


def test_build_tree_L1_drive_extraction_is_idempotent(tmp_path):
    # calling build_tree twice on the same L1 root should not re-extract
    # or duplicate the extracted folder
    project_dir = tmp_path / "2016.1.01114.V"
    project_dir.mkdir()
    _make_archive(project_dir, "extract1", contents={"a.csv": "data"})

    tree1 = build_tree(tmp_path, None, data_type="L1")
    extract_keys1 = [k for k in tree1["2016.1.01114.V"] if k not in ("meta",)]

    tree2 = build_tree(tmp_path, None, data_type="L1")
    extract_keys2 = [k for k in tree2["2016.1.01114.V"] if k not in ("meta",)]

    assert extract_keys1 == extract_keys2, \
        f"re-running build_tree expected the same extracted folder names, \
            got {extract_keys1} and {extract_keys2}"
    

def test_build_tree_L1_multi_level_nesting_to_drive(tmp_path):
    # root -> project -> extract -> drive, two real subfolder levels deep
    project_dir = tmp_path / "2016.1.01114.V"
    extract_dir = project_dir / "group.uid___A001_extract"
    extract_dir.mkdir(parents=True)
    _make_archive(
        extract_dir, "3600",
        contents={"SR1_M87_2017_095_hi.csv": "data"},
    )
    fmt = "SR1_M87_{year}_{day}_{band}.csv"
    tree = build_tree(tmp_path, fmt, data_type="L1")

    project = tree["2016.1.01114.V"]
    assert "group.uid___A001_extract" in project, \
        "second nesting level not recursed into"

    extract = project["group.uid___A001_extract"]
    drive_keys = [k for k in extract if k not in ("meta",)]
    assert len(drive_keys) == 1, f"expected one extracted drive, got {drive_keys}"

    extracted = extract[drive_keys[0]]
    assert "data" in extracted, "innermost extracted drive should be L2"
    assert len(extracted["data"]) == 1,\
        f"expected 1 fmt match at innermost level, got {list(extracted['data'].keys())}"


def test_build_tree_L1_subfolder_and_drive_at_same_level(tmp_path):
    project_dir = tmp_path / "2016.1.01114.V"
    project_dir.mkdir()
    nested = project_dir / "nested_subdir"
    nested.mkdir()
    (nested / "README.txt").write_text("readme", encoding="utf-8")
    _make_archive(project_dir, "extract1", contents={"a.csv": "data"})

    fmt = "{name}.csv"
    tree = build_tree(tmp_path, fmt, data_type="L1")
    project = tree["2016.1.01114.V"]

    assert "nested_subdir" in project, "real subfolder missing"
    assert "data" not in project["nested_subdir"], \
        "real subfolder should stay L1 (no data key)"

    drive_keys = [k for k in project if k not in ("meta", "nested_subdir")]
    assert len(drive_keys) == 1, f"expected one extracted drive, got {drive_keys}"
    assert "data" in project[drive_keys[0]], \
        "extracted drive should be L2 (has data key)"


def test_build_tree_L1_fmt_propagates_through_nested_extraction(tmp_path):
    project_dir = tmp_path / "2016.1.01114.V"
    extract_dir = project_dir / "group.uid___extract"
    extract_dir.mkdir(parents=True)
    _make_archive(
        extract_dir, "drive1",
        contents={"CUSTOM_2017_095_hi.dat": "data"},
    )
    custom_fmt = "CUSTOM_{year}_{day}_{band}.dat"
    tree = build_tree(tmp_path, custom_fmt, data_type="L1")

    extract = tree["2016.1.01114.V"]["group.uid___extract"]
    drive_keys = [k for k in extract if k not in ("meta",)]
    extracted = extract[drive_keys[0]]

    assert custom_fmt in extracted["data"], \
        f"explicit fmt did not propagate through nested L1 recursion, got keys:\
              {list(extracted['data'].keys())}"


def test_build_tree_L1_multiple_drives_get_distinct_keys(tmp_path):
    project_dir = tmp_path / "2016.1.01114.V"
    project_dir.mkdir()
    _make_archive(project_dir, "extractA", contents={"a.csv": "data"})
    _make_archive(project_dir, "extractB", contents={"b.csv": "data"})

    tree = build_tree(tmp_path, None, data_type="L1")
    project = tree["2016.1.01114.V"]

    drive_keys = [k for k in project if k not in ("meta",)]
    assert len(drive_keys) == 2, f"expected two distinct extracted drives, \
        got {drive_keys}"
    assert len(set(drive_keys)) == 2, "extracted drive keys collided"


def test_build_tree_L1_empty_folder_does_not_crash(tmp_path):
    project_dir = tmp_path / "2016.1.01114.V"
    # genuinely empty, no files, no subfolders, no drives
    project_dir.mkdir()  
    tree = build_tree(tmp_path, None, data_type="L1")

    assert "2016.1.01114.V" in tree
    empty_project = tree["2016.1.01114.V"]
    assert "meta" not in empty_project, "no files should mean no meta key"
    assert "data" not in empty_project, "L1 level should never have a data key"

def test_build_tree_L1_does_not_resync_modified_extraction(tmp_path):
    project_dir = tmp_path / "2016.1.01114.V"
    project_dir.mkdir()
    _make_archive(
        project_dir, "extract1",
        contents={"a.csv": "data", "b.csv": "data"},
    )

    tree1 = build_tree(tmp_path, "{name}.csv", data_type="L1")
    drive_keys = [k for k in tree1["2016.1.01114.V"] if k not in ("meta",)]
    extracted_dir = project_dir / drive_keys[0]

    # simulate someone manually deleting a file from the extracted folder
    (extracted_dir / "b.csv").unlink()

    tree2 = build_tree(tmp_path, "{name}.csv", data_type="L1")
    extracted2 = tree2["2016.1.01114.V"][drive_keys[0]]
    fmt_dict = extracted2["data"]["{name}.csv"]
    all_paths = set(path for stem_pf in fmt_dict.values() for path in stem_pf["path"])
    assert any("a.csv" in p for p in all_paths), \
        "expected a.csv to be present in the extracted drive"
    assert not any("b.csv" in p for p in all_paths), \
        "expected b.csv to be absent from the extracted drive"


### explicit fmt optional/missing parameter tests ###

def test_build_tree_explicit_fmt_drops_missing_parameter(tmp_path):
    (tmp_path / "a0_i30.csv").write_text("data", encoding="utf-8")
    (tmp_path / "a0.csv").write_text("data", encoding="utf-8")
    fmt = "a{p0}_{p1}"
    tree = build_tree(tmp_path, fmt)
    assert fmt in tree["data"], f"expected fmt key {fmt!r}, \
                            got {list(tree['data'].keys())}"
    all_rows = []
    for stem_pf in tree["data"][fmt].values():
        all_rows.extend(stem_pf.to_dict("records"))
    import pandas as pd
    all_pf = pd.DataFrame(all_rows)
    assert len(all_pf) == 2, f"expected 2 files matched, got {len(all_pf)} rows"
    missing_row = all_pf[all_pf["path"] == "a0.csv"]
    assert missing_row["p1"].isna().all(), f"expected p1 to be NaN for missing\
                                     parameter, got {missing_row['p1']}"


def test_build_tree_explicit_fmt_fused_token_no_missing_variant(tmp_path):
    (tmp_path / "a0_i30.csv").write_text("data", encoding="utf-8")
    fmt = "a{p0}_i{p1}"
    tree = build_tree(tmp_path, fmt)
    assert fmt in tree["data"], f"expected fmt key {fmt!r}, \
                                    got {list(tree['data'].keys())}"
    all_rows = []
    for stem_pf in tree["data"][fmt].values():
        all_rows.extend(stem_pf.to_dict("records"))
    import pandas as pd
    all_pf = pd.DataFrame(all_rows)
    assert len(all_pf) == 1, f"expected 1 file matched, got {len(all_pf)} rows"
    assert all_pf.iloc[0]["p0"] == "0", f"expected p0 to be '0', \
                                    got {all_pf.iloc[0]['p0']}"
    assert all_pf.iloc[0]["p1"] == "30", f"expected p1 to be '30', \
                                    got {all_pf.iloc[0]['p1']}"

### auto-detection single-file rejection tests ###

def test_detect_fmt_rejects_single_file_with_no_siblings(tmp_path):
    # a genuinely unique file with no siblings sharing its structure
    # should not produce a degenerate, parameter-free fmt
    (tmp_path / "uniquefile_v1.dat").write_text("data", encoding="utf-8")
    fmts = detect_fmt(tmp_path)
    assert fmts == [], \
        f"expected no fmt for a lone file with no siblings, got {fmts}"


def test_build_tree_single_unmatched_file_falls_to_meta(tmp_path):
    (tmp_path / "uniquefile_v1.dat").write_text("data", encoding="utf-8")
    tree = build_tree(tmp_path)  # fmt=None, auto-detect
    assert "data" not in tree, "lone unique file should not produce a data branch"
    assert "uniquefile_v1.dat" in list(tree["meta"]["path"]), \
        "lone unique file should land in meta"


### case-insensitive extension matching tests ###

def test_detect_fmt_excludes_meta_extension_case_insensitively(tmp_path):
    # .PY (uppercase) should be excluded the same as .py
    (tmp_path / "SR1_M87_2017_095_hi.csv").write_text("data", encoding="utf-8")
    (tmp_path / "SR1_M87_2017_096_lo.csv").write_text("data", encoding="utf-8")
    (tmp_path / "dump_csv.PY").write_text("data", encoding="utf-8")
    fmts = detect_fmt(tmp_path)
    assert all("dump" not in fmt for fmt in fmts), \
        f"uppercase .PY script leaked into fmts: {fmts}"


def test_build_tree_drives_match_extension_case_insensitively(tmp_path):
    _make_archive(tmp_path, "data1", "zip")
    tree = build_tree(tmp_path, "{name}")
    if "data" in tree:
        for fmt_dict in tree["data"].values():
            for stem_pf in fmt_dict.values():
                for path in stem_pf["path"]:
                    assert not path.lower().endswith(".zip"), \
                        f"uppercase archive leaked into data branch: {path}"


### zero-literal-anchor merge rejection tests ###

def test_detect_fmt_does_not_merge_completely_unrelated_fmts(tmp_path):
    # two fmts that share no literal token anywhere should NOT merge into
    # one fully-parameterized, zero-literal fmt
    (tmp_path / "A_B_C_D.csv").write_text("data", encoding="utf-8")
    (tmp_path / "A_E_F_G.csv").write_text("data", encoding="utf-8")
    (tmp_path / "H_I_J_K.csv").write_text("data", encoding="utf-8")
    (tmp_path / "L_I_M_N.csv").write_text("data", encoding="utf-8")
    fmts = detect_fmt(tmp_path)
    assert len(fmts) == 2, \
        f"expected 2 separate fmts (no shared literal across all 4), got {fmts}"
    for fmt in fmts:
        assert "{p0}_{p1}_{p2}_{p3}" != fmt, \
            f"fmt should not be fully parameterized with zero literals: {fmt}"
        

### build_repo tests ###

def test_build_repo_creates_hm_directory(built_repo):
    assert Path(built_repo.dothm.path).is_dir(), \
        "expected .hm directory to be created"


def test_build_repo_returns_repo_instance(built_repo):
    assert isinstance(built_repo, Repo), \
        f"expected Repo instance, got {type(built_repo)}"
    
    
def test_build_repo_raises_if_path_exists_and_no_overwrite(dataset, repo_path):
    tree = build_tree(dataset, FMT, data_type="L2")
    build_repo(tree=tree, repo_path=repo_path,
               dataset_name=DATASET, worktree_root=dataset)
    with pytest.raises(FileExistsError):
        build_repo(tree=tree, repo_path=repo_path,
                   dataset_name=DATASET, worktree_root=dataset)
        

def test_build_repo_overwrites_existing_repo(dataset, repo_path):
    tree = build_tree(dataset, FMT, data_type="L2")
    build_repo(tree=tree, repo_path=repo_path,
               dataset_name=DATASET, worktree_root=dataset)
    repo = build_repo(tree=tree, repo_path=repo_path,
                      dataset_name=DATASET, worktree_root=dataset,
                      overwrite=True)
    assert isinstance(repo, Repo), f"expected Repo instance after overwrite, \
                                    got {type(repo)}"
    

def test_build_repo_main_meta_contains_dataset_name(built_repo):
    assert built_repo.state.meta.get("dataset") == DATASET, \
        f"expected dataset name in meta.yml, got {built_repo.state.meta}"


def test_build_repo_main_meta_contains_file_list(built_repo):
    files = built_repo.state.meta.get("files", [])
    assert len(files) > 0, "expected meta file list to be non-empty"
    assert any("README" in f for f in files), \
        "expected README.md in meta file list"
    

def test_build_repo_branch_names_are_sanitized(built_repo):
    names = built_repo.branches()["names"]
    for name in names:
        assert "{" not in name and "}" not in name, \
            f"branch name contains invalid git characters: {name}"
        

def test_build_repo_branch_names_follow_fmt_slash_stem_pattern(built_repo):
    names = [n for n in built_repo.branches()["names"] if n != "main"]
    for name in names:
        assert "/" in name, \
            f"expected fmt/stem pattern in branch name, got {name}"
        

def test_build_repo_creates_correct_number_of_branches(built_repo):
    names = built_repo.branches()["names"]
    assert len(names) == 4, \
        f"expected 4 branches (3 stems + main), got {len(names)}"


def test_build_repo_main_branch_always_exists(built_repo):
    assert "main" in built_repo.branches()["names"], \
        "expected main branch to always exist"
    

def test_build_repo_config_contains_original_fmt(built_repo):
    names = [n for n in built_repo.branches()["names"] if n != "main"]
    for branch in names:
        built_repo.dothm.git.checkout(branch)
        built_repo.state = built_repo.dothm.load()
        fmt = built_repo.state.config["data"][0]["fmt"]
        assert fmt == FMT, \
            f"expected original fmt in config.yml, got {fmt}"
    built_repo.dothm.git.checkout("main")
    built_repo.state = built_repo.dothm.load()


def test_build_repo_config_fmt_has_curly_braces(built_repo):
    names = [n for n in built_repo.branches()["names"] if n != "main"]
    built_repo.dothm.git.checkout(names[0])
    built_repo.state = built_repo.dothm.load()
    fmt = built_repo.state.config["data"][0]["fmt"]
    assert "{" in fmt and "}" in fmt, \
        f"config.yml fmt should contain curly braces, got {fmt}"
    built_repo.dothm.git.checkout("main")
    built_repo.state = built_repo.dothm.load()


### data.tsv per branch ###

def test_build_repo_data_tsv_has_sha1_column(built_repo):
    names = [n for n in built_repo.branches()["names"] if n != "main"]
    for branch in names:
        data = pd.read_csv(
            StringIO(built_repo.dothm.git.show(f"{branch}:data.tsv")),
            sep="\t", dtype=str)
        assert "sha1" in data.columns, \
            f"expected sha1 column in {branch}:data.tsv"


def test_build_repo_data_tsv_has_correct_row_count(built_repo):
    names = [n for n in built_repo.branches()["names"] if n != "main"]
    for branch in names:
        data = pd.read_csv(
            StringIO(built_repo.dothm.git.show(f"{branch}:data.tsv")),
            sep="\t", dtype=str)
        assert len(data) == 2, \
            f"expected 2 files per stem (csv+txt), got {len(data)} in {branch}"


def test_build_repo_data_tsv_has_parameter_columns(built_repo):
    names = [n for n in built_repo.branches()["names"] if n != "main"]
    for branch in names:
        data = pd.read_csv(
            StringIO(built_repo.dothm.git.show(f"{branch}:data.tsv")),
            sep="\t", dtype=str)
        param_cols = [c for c in data.columns if c != "sha1"]
        assert len(param_cols) > 0, \
            f"expected parameter columns in {branch}:data.tsv"


### optional parameter handling ###

def test_build_repo_optional_param_is_nan_when_missing(built_repo):
    names = [n for n in built_repo.branches()["names"] if n != "main"]
    missing_method_branch = next(
        (n for n in names if "096_hi_hops" in n), None)
    assert missing_method_branch is not None, \
        "expected a branch for stem without {method}"
    data = pd.read_csv(
        StringIO(built_repo.dothm.git.show(f"{missing_method_branch}:data.tsv")),
        sep="\t", dtype=str)
    assert "method" in data.columns, \
        "expected method column even when value is missing"
    assert data["method"].isna().all(), \
        "expected NaN for method in stem that has no method parameter"


### objects stored ###

def test_build_repo_objects_stored_for_each_file(built_repo):
    objects_dir = Path(built_repo.dothm.path) / "objects"
    object_files = [f for f in objects_dir.rglob("*") if f.is_file()]
    assert len(object_files) == 3, \
        f"expected 3 unique objects stored, got {len(object_files)}"


def test_build_repo_object_sha1_matches_filename(built_repo, repo_path):
    objects_dir = repo_path / ".hm" / "objects"
    for obj_file in objects_dir.rglob("*"):
        if not obj_file.is_file():
            continue
        expected_sha1 = obj_file.parent.name + obj_file.name
        actual_sha1 = Repo.checksum(obj_file)
        assert actual_sha1 == expected_sha1, \
            f"object file sha1 mismatch: expected {expected_sha1}, got {actual_sha1}"


### error fallback ###

def test_build_repo_error_branch_still_committed(dataset, repo_path, monkeypatch):
    import hallmark.eht_datatree as edt
    def always_fail(pf, fmt):
        raise RuntimeError("forced test failure")
    monkeypatch.setattr(edt, "manifest_frame_from_pf", always_fail)
    tree = build_tree(dataset, FMT, data_type="L2")
    repo = build_repo(
        tree=tree,
        repo_path=repo_path,
        dataset_name=DATASET,
        worktree_root=dataset,)
    names = [n for n in repo.branches()["names"] if n != "main"]
    assert len(names) == 3, \
        f"expected 3 branches even with manifest failure, got {len(names)}"


def test_build_repo_error_branch_has_error_in_meta(dataset, repo_path, monkeypatch):
    import hallmark.eht_datatree as edt
    def always_fail(pf, fmt):
        raise RuntimeError("forced test failure")
    monkeypatch.setattr(edt, "manifest_frame_from_pf", always_fail)
    tree = build_tree(dataset, FMT, data_type="L2")
    repo = build_repo(
        tree=tree,
        repo_path=repo_path,
        dataset_name=DATASET,
        worktree_root=dataset,)
    names = [n for n in repo.branches()["names"] if n != "main"]
    repo.dothm.git.checkout(names[0])
    repo.state = repo.dothm.load()
    assert "error" in repo.state.meta, \
        "expected error key in meta.yml when manifest fails"
    assert "files" in repo.state.meta, \
        "expected files list in meta.yml when manifest fails"
    repo.dothm.git.checkout("main")
    repo.state = repo.dothm.load()


### returns to main ###

def test_build_repo_ends_on_main_branch(built_repo):
    assert built_repo.branches()["current"] == "main", \
        "expected repo to be on main branch after build_repo completes"


def test_build_repo_main_state_reflects_main_branch(built_repo):
    assert built_repo.state.meta.get("dataset") == DATASET, \
        "expected main branch meta after build_repo completes"
    assert built_repo.state.data.empty, \
        "expected empty data.tsv on main branch"