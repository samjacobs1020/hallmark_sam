import pytest
import shutil
import yaml
from pathlib import Path
import hallmark

ORIGINAL_YAML = Path("demos/data/.hallmark.yaml")

@pytest.fixture(scope="function")
def encodings_yaml(tmp_path):
    tmp_yaml = tmp_path / ".hallmark.yaml"
    shutil.copy2(ORIGINAL_YAML, tmp_yaml)
    hallmark.set_rel_yaml_path(tmp_yaml)
    return tmp_yaml

@pytest.fixture(scope="function", autouse=True)
def _append_tmp_path_entries_to_encodings_yaml(tmp_path, encodings_yaml):
    encodings_yaml.write_text("data: []\n", encoding="utf-8")
    y = yaml.safe_load(encodings_yaml.read_text(encoding="utf-8")) or {}
    y.setdefault("data", [])
    fmts = [
        "/a_{a:d}/b_{b:d}.txt",
        "/a{aspin}/b_{b:d}.txt",
        "/{mag:d}_mag{aspin}_w{win:d}.h5",
    ]
    for fmt in fmts:
        y["data"].append(
            {
                "fmt": fmt,
                "encoding": {"aspin": r"m([0-9]+(\.[0-9]+)?|\.[0-9]+)"},
            }
        )
    encodings_yaml.write_text(yaml.safe_dump(y, sort_keys=False), encoding="utf-8")
    yield

def spin_format(val):
    if val == 0:
        return "0"
    return f"{val:+g}"

@pytest.fixture(scope = "function")
def create_temp_data(tmp_path):
    data_dir = tmp_path
    print(data_dir)
    for a in range(10):
        subdir = data_dir / f"a_{a}"
        subdir.mkdir(parents=True)
        for b in range(10, 20):
            (subdir / f"b_{b}.txt").touch()
    return data_dir

@pytest.fixture(scope = "function")
def create_temp_data_spin(tmp_path):
    data_dir = tmp_path
    spins = [-0.5, 0.0, 0.5]
    for a in spins:
        subdir = data_dir / f"a{spin_format(a)}"
        subdir.mkdir(parents=True)
        for b in range(10, 20):
            (subdir / f"b_{b}.txt").touch()
    return data_dir

@pytest.fixture(scope = "function")
def create_temp_data_spin_with_m(tmp_path):
    data_dir = tmp_path
    spins = ["m0.5", "0", "0.5"]
    
    for mag in range(0, 2):   
        for aspin in spins:       
            for win in range(10, 20):  
                file_name = f"{mag}_mag{aspin}_w{win}.h5"
                (data_dir / file_name).touch()
    return data_dir