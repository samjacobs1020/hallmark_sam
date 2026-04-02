import pandas as pd

from hallmark import Repo
from hallmark import ParaFrame


### Ensure ParaFrame type
def test_standard_pf_is_paraframe(hallmark_test_suite_dictionary):
    assert isinstance(hallmark_test_suite_dictionary["standard_pf"], ParaFrame)

def test_encoded_pf_is_paraframe(hallmark_test_suite_dictionary):
    assert isinstance(hallmark_test_suite_dictionary["encoded_pf"], ParaFrame)

### Test Standard pf
def test_standard_pf_shape(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["standard_pf"]
    assert pf.shape == (12, 3)

def test_standard_pf_column_names(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["standard_pf"]
    assert set(pf.columns) == {"path", "a", "i"}

def test_standard_pf_column_value_types(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["standard_pf"]
    assert pd.api.types.is_float_dtype(pf["a"])
    assert pd.api.types.is_float_dtype(pf["i"])

def test_standard_pf_values(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["standard_pf"]
    assert set(pf["a"].unique()) == {0.0, 0.75, 0.975}
    assert set(pf["i"].unique()) == {0.0, 30.0, 60.0, 90.0}

def test_standard_pf_paths_match_created_files(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["standard_pf"]
    assert sorted(pf["path"]) == sorted(
        hallmark_test_suite_dictionary["standard_files"])

def test_standard_pf_supports_pandas_methods(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["standard_pf"]
    assert isinstance(pf.head(), pd.DataFrame)

def test_standard_glob_pattern_created_properly(hallmark_test_suite_dictionary):
    pattern = hallmark_test_suite_dictionary["standard_glob_pattern"].replace("\\", "/")
    assert pattern.endswith("/a*_i*.h5")

def test_standard_glob_returns_expected_files(hallmark_test_suite_dictionary):
    files = hallmark_test_suite_dictionary["standard_globbed_files"]
    assert len(files) == 16

def test_standard_pf_single_filter_argument(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["standard_pf"]
    filtered = pf(a=0.75)
    assert len(filtered) == 4
    assert set(filtered["a"].unique()) == {0.75}

def test_standard_pf_filter_multiple_values(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["standard_pf"]
    filtered = pf(a=[0.75, 0.975])
    assert len(filtered) == 8
    assert set(filtered["a"].unique()) == {0.75, 0.975}

def test_standard_pf_filter_multiple_conditions(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["standard_pf"]
    filtered = pf(a=0.75)(i=0)
    assert len(filtered) == 1
    assert set(filtered["a"].unique()) == {0.75}
    assert set(filtered["i"].unique()) == {0}

### Test encoded pf
def test_encoded_pf_shape(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["encoded_pf"]
    assert pf.shape == (16, 3)

def test_encoded_pf_column_names(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["encoded_pf"]
    assert set(pf.columns) == {"path", "aspin", "i"}

def test_encoded_pf_has_custom_spin_type(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["encoded_pf"]
    assert pd.api.types.is_float_dtype(pf["aspin"])

def test_encoded_pf_spin_values(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["encoded_pf"]
    assert set(pf["aspin"].unique()) == {-0.5, 0, 0.75, 0.975}

def test_encoded_pf_i_values(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["encoded_pf"]
    assert set(pf["i"].unique()) == {0.0, 30.0, 60.0, 90.0}

def test_encoded_pf_filter_single_value(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["encoded_pf"]
    filtered = pf(aspin=-0.5)
    assert len(filtered) == 4
    assert set(filtered["aspin"].unique()) == {-0.5}

def test_encoded_pf_filter_multiple_values(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["encoded_pf"]
    filtered = pf(aspin=[-0.5, 0.0])
    assert len(filtered) == 8
    assert set(filtered["aspin"].unique()) == {-0.5, 0.0}

def test_encoded_pf_filter_multiple_conditions(hallmark_test_suite_dictionary):
    pf = hallmark_test_suite_dictionary["encoded_pf"]
    filtered = pf(aspin=-0.5)(i=0)
    assert len(filtered) == 1
    assert set(filtered["aspin"].unique()) == {-0.5}
    assert set(filtered["i"].unique()) == {0}

def test_encoded_glob_pattern_created_properly(hallmark_test_suite_dictionary):
    pattern = hallmark_test_suite_dictionary["encoded_glob_pattern"].replace("\\", "/")
    assert pattern.endswith("/a*_i*.h5")

def test_encoded_glob_returns_expected_files(hallmark_test_suite_dictionary):
    files = hallmark_test_suite_dictionary["encoded_globbed_files"]
    assert len(files) == 16

### Test repo behavior
def test_repo_init_created_dot_hm(hallmark_test_suite_dictionary):
    repo_path = hallmark_test_suite_dictionary["repo_path"]
    assert (repo_path / ".hm").is_dir()

def test_repo_add_result_has_expected_length(hallmark_test_suite_dictionary):
    result = hallmark_test_suite_dictionary["add_result"]
    assert len(result) == 12

def test_repo_add_result_paths_match_standard_files(hallmark_test_suite_dictionary):
    result = hallmark_test_suite_dictionary["add_result"]
    assert sorted(result["path"]) == sorted(
        hallmark_test_suite_dictionary["standard_files"])

def test_repo_commit_succeeds(hallmark_test_suite_dictionary):
    assert hallmark_test_suite_dictionary["commit_result"] is True

def test_data_tsv_and_worktree_reconstruction(hallmark_test_suite_dictionary):
    repo = Repo(hallmark_test_suite_dictionary["repo_path"])
    assert len(repo.state.data) == 12
    assert repo.worktree.stem == "repo"